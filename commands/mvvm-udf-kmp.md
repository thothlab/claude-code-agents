# MVVM + UDF Rules для KMP/CMP

You are an expert in MVVM + Unidirectional Data Flow (UDF) for Kotlin Multiplatform (KMP) and Compose Multiplatform (CMP) projects.

Apply ALL rules below when generating, reviewing, or refactoring code.

**Core pattern: MVVM + UDF. Do NOT use MVI** — no Reducer functions, no Intent/Effect sealed classes as primary pattern.

---

## 0. КЛЮЧЕВАЯ ИДЕЯ ДЛЯ KMP

**ViewModel — это контейнер lifecycle, а не контейнер логики.**

В KMP логика живёт в платформо-независимом классе (`UIModel`) в `commonMain`, а Android `ViewModel` — это тонкая обёртка-делегат, которая привязывает UIModel к Android lifecycle. iOS и Web получают UIModel напрямую через DI.

Ниже описаны два допустимых паттерна реализации:

- **Паттерн A — UIModel + ViewModel separation (предпочтительный для KMP/CMP).** Реактивный стиль через `combine` / `flatMapLatest` / `stateIn(WhileSubscribed)`. Используйте по умолчанию для shared логики.
- **Паттерн B — ViewStateDelegate (`reduce` / `asyncReduce`).** Императивный стиль для простых Android-центричных экранов или там, где состояние меняется только в ответ на UI-команды и нет каскадных реактивных зависимостей. Может использоваться поверх UIModel либо самостоятельно в Android-only ViewModel.

Не смешивайте паттерны внутри одного экрана. Внутри проекта допустимо иметь оба.

---

## 1. АРХИТЕКТУРНЫЕ СЛОИ

### Два верхнеуровневых слоя
- **Core (Data Layer)** — репозитории, remote/local DataSource, кэширование, Use Cases
- **UI Layer** — UIModels/ViewModels, Composable screens, навигация

Для крупных проектов добавляйте `uikit` (shared UI компоненты) и `tools` (утилиты) как отдельные модули. Не создавайте их спекулятивно для небольших приложений.

### Repository — единственный авторитет данных
Repository решает:
- откуда брать данные (remote API или локальный кэш)
- на каком coroutine dispatcher работать
- кэшировать ли и как долго

**Запрещено** принимать эти решения в UIModel/ViewModel или UI.

### Use Cases — `fun interface`
UIModel зависит от use case'ов, не от репозиториев напрямую. Каждый use case — однометодный `fun interface`. Это упрощает тесты (lambda-fakes без mocking-библиотек).

```kotlin
fun interface GetArtistsForGenreUseCase {
    operator fun invoke(genreId: String): Flow<ImmutableList<Artist>>
}
```

---

## 2. ПАТТЕРН A — UIModel + ViewModel separation (KMP/CMP)

### Интерфейс UIModel (commonMain)

```kotlin
interface UIModel<UIState, UICommand> {
    val scope: CoroutineScope          // injected, not hardcoded
    val uiState: StateFlow<UIState>
    fun sendCommand(command: UICommand)
}
```

### Реализация UIModel (commonMain, без Android imports)

```kotlin
class MusicDiscoveryUIModel(
    override val scope: CoroutineScope,           // injected per platform
    getGenres: GetGenresUseCase,
    getArtistsForGenre: GetArtistsForGenreUseCase,
) : UIModel<MusicDiscoveryUIState, MusicDiscoveryCommand> {

    private val selectedGenre = MutableStateFlow<Genre?>(null)
    private val selectedArtist = MutableStateFlow<Artist?>(null)

    private val artists = selectedGenre.flatMapLatest { genre ->
        if (genre != null) getArtistsForGenre(genre.id)
        else flowOf(persistentListOf())
    }

    override val uiState: StateFlow<MusicDiscoveryUIState> = combine(
        getGenres(), selectedGenre, artists, selectedArtist,
        ::MusicDiscoveryUIState,                  // конструктор-референс — порядок параметров обязан совпасть
    ).stateIn(scope, SharingStarted.WhileSubscribed(5_000), MusicDiscoveryUIState.Default)

    override fun sendCommand(command: MusicDiscoveryCommand) {
        when (command) {
            is SelectGenre -> {
                selectedGenre.value = command.genre
                selectedArtist.value = null       // каскадный сброс downstream
            }
            is SelectArtist -> selectedArtist.value = command.artist
        }
    }
}
```

### Android ViewModel — 3 строки

```kotlin
class MusicDiscoveryViewModel(
    uiModel: MusicDiscoveryUIModel,
) : ViewModel(uiModel.scope),
    UIModel<MusicDiscoveryUIState, MusicDiscoveryCommand> by uiModel
```

- `ViewModel(scope)` сохраняет scope как `Closeable` (Lifecycle 2.8.0+) — он отменяется в `onCleared()` автоматически.
- `by uiModel` делегирует все методы интерфейса в UIModel.

### Структуры данных

- `UIState` — `data class` с companion `Default` (initial state для `stateIn`)
- `UICommand` — `sealed interface` (исчерпывающий `when` в `sendCommand`)
- Коллекции в `UIState` — `ImmutableList` из `kotlinx.collections.immutable` (Compose считает stable, нет лишних рекомпозиций)

### Реактивная связка через `flatMapLatest`

`flatMapLatest` отменяет предыдущий fetch и очищает downstream при смене upstream-значения — никакой ручной очистки.

### `stateIn(SharingStarted.WhileSubscribed(5_000), Default)` — обязательно

- В паре с `collectAsStateWithLifecycle()` upstream-flows останавливаются через 5 секунд после ухода в фон
- 5-секундный таймаут переживает config changes (поворот экрана < 5с)
- `collectAsStateWithLifecycle` мультиплатформенен с Lifecycle 2.8.0+
- С `Eagerly` upstream работает в фоне — расход батареи
- `onStart {}` с `WhileSubscribed` срабатывает у первого подписчика (правильно). С `Eagerly` — в момент конструирования (слишком рано)

> ⚠️ `combine` из `kotlinx.coroutines` поддерживает максимум 5 параметров. Для 6+ flows напишите кастомный extension.

---

## 3. ПАТТЕРН B — ViewStateDelegate (императивный reduce)

Для простых экранов без каскадных реактивных зависимостей используйте делегат, устраняющий бойлерплейт `MutableStateFlow + Mutex`.

| Член | Тип | Назначение |
|------|-----|-----------|
| `uiState` | `Flow<UIState>` | Стрим состояния для UI |
| `stateValue` | `UIState` | Синхронное чтение текущего состояния |
| `singleEvents` | `Flow<Event>` | Стрим разовых событий |
| `reduce` | `suspend (UIState) -> UIState` | Обновление состояния под Mutex |
| `asyncReduce` | `CoroutineScope.(UIState) -> UIState` | Неблокирующее обновление |
| `sendEvent` | `suspend (Event) -> Unit` | Отправка разового события |

`reduce` ОБЯЗАН использовать `Mutex` для предотвращения конкурентной порчи состояния.

```kotlin
class LoginViewModel(
    private val authRepository: AuthRepository,
) : ViewModel(),
    ViewStateDelegate<UiState, Event> by ViewStateDelegateImpl(UiState()) {

    data class UiState(
        val isLoading: Boolean = false,
        val login: String = "",
        val password: String = "",
    )

    sealed interface Event { data object GoToHome : Event }

    fun onLoginChange(login: String) {
        viewModelScope.asyncReduce { it.copy(login = login) }
    }

    fun onLoginClick() {
        viewModelScope.launch {
            reduce { it.copy(isLoading = true) }
            authRepository.login(stateValue.login, stateValue.password)
            sendEvent(Event.GoToHome)
        }.invokeOnCompletion {
            viewModelScope.asyncReduce { it.copy(isLoading = false) }
        }
    }
}
```

В KMP версии этого паттерна `viewModelScope` заменяется на инжектируемый `CoroutineScope`, а сам `ViewStateDelegate` живёт в `commonMain`.

---

## 4. ПРАВИЛА UiState (общие для A и B)

### Один immutable state-объект на экран
Всегда `data class` с дефолтными значениями. Никогда не разбрасывайте состояние по нескольким `StateFlow` свойствам.

```kotlin
data class UiState(
    val isLoading: Boolean = false,
    val isError: Boolean = false,
    val items: ImmutableList<ItemUiState> = persistentListOf(),
) {
    companion object { val Default = UiState() }
}
```

### State — read-only за пределами UIModel/ViewModel
UI **никогда** не мутирует состояние напрямую. Единственная точка мутации — `sendCommand` (паттерн A) или `reduce`/`asyncReduce` (паттерн B).

### Явное моделирование loading и error
`UiState` ДОЛЖЕН содержать `isLoading` и `isError` (или `errorMessage: String?`). Никаких неявных состояний загрузки или исключений, утекающих в UI.

### Производные состояния — внутри UIModel/ViewModel
Если кнопка должна показываться при `isLoggedIn && isPremium` — вычислите это в UIModel и положите готовое поле в `UiState`. Не комбинируйте сырые булевы в Composable.

---

## 5. SINGLE LIVE EVENTS (разовые эффекты)

Применимо в обоих паттернах — для навигации, snackbar/toast, закрытия экрана. Для постоянного UI-состояния используйте поля `UiState`.

В паттерне A события проще выразить полем `UiState` (`val navigateTo: NavTarget? = null`) с обязательным «consumed» подтверждением, либо отдельным `Channel`-полем UIModel.

### Канал, не SharedFlow

```kotlin
private val singleEventsChannel = Channel<Event>(Channel.BUFFERED)
val singleEvents: Flow<Event> = singleEventsChannel.receiveAsFlow()
```

### Сбор событий с lifecycle

```kotlin
LaunchedEffect(Unit) {
    viewModel.singleEvents.collect { event ->
        when (event) {
            is Event.GoToHome -> navController.navigate(...)
        }
    }
}
```

---

## 6. ПЛАТФОРМЕННАЯ ПРИВЯЗКА SCOPE

`CoroutineScope` — единственное, что меняется между платформами. Никаких `expect/actual` для логики.

| Платформа | Scope |
|-----------|-------|
| **Android** | `CoroutineScope(Dispatchers.Main.immediate + SupervisorJob())` через DI → передаётся в UIModel; ViewModel-обёртка вызывает `ViewModel(uiModel.scope)` |
| **Kobweb / Web** | `CoroutineScope(SupervisorJob())` — DI инжектит UIModel напрямую |
| **iOS (SwiftUI)** | KoinHelper достаёт UIModel; Swift structured concurrency управляет lifecycle |

---

## 7. ПРАВИЛА COMPOSE UI (CMP)

### Экраны — stateless Composable
Composable-функции экранов получают `uiState` и колбэки, не ViewModel напрямую (кроме корневого уровня для связки).

### Сбор состояния с lifecycle safety

```kotlin
val uiState by viewModel.uiState.collectAsStateWithLifecycle()
```

На таргетах без `collectAsStateWithLifecycle` (старые Lifecycle) используйте `collectAsState()`.

### Никакой бизнес-логики в Composable
Composable только: рендерит состояние, передаёт жесты в `sendCommand`/функции ViewModel. Никаких `if/when` по сырым данным.

### Передавайте отдельные лямбды, не весь ViewModel

```kotlin
// ПРАВИЛЬНО
LoginScreen(
    uiState = uiState,
    onLoginChange = viewModel::onLoginChange,
    onLoginClick = viewModel::onLoginClick,
)

// или для паттерна A
MusicDiscoveryScreen(
    uiState = uiState,
    onCommand = viewModel::sendCommand,
)

// НЕПРАВИЛЬНО
LoginScreen(viewModel = viewModel)
```

---

## 8. COROUTINES И THREADING

- Весь async — в инжектированном `scope` (KMP/UIModel) или `viewModelScope` (Android-only ViewModel)
- Repository функции — `suspend`, dispatcher-aware внутри
- Никогда не используйте `GlobalScope`
- В паттерне B используйте `invokeOnCompletion` для сброса `isLoading` независимо от успеха/ошибки
- В паттерне A `flatMapLatest` сам отменяет stale работу — ручных флагов не нужно

---

## 9. ТЕСТИРОВАНИЕ

### Чистый Kotlin, без Android
**Никаких** `Dispatchers.setMain()`, Robolectric, mock-библиотек.

### Паттерн `createSut` (для UIModel)

```kotlin
private fun TestScope.createSut(
    getGenres: GetGenresUseCase = fakeGenres,
    getArtistsForGenre: GetArtistsForGenreUseCase = fakeArtists,
): Pair<MusicDiscoveryUIModel, MutableList<MusicDiscoveryUIState>> {
    val sut = MusicDiscoveryUIModel(
        scope = backgroundScope,                  // НЕ TestScope!
        getGenres = getGenres,
        getArtistsForGenre = getArtistsForGenre,
    )
    val states = mutableListOf<MusicDiscoveryUIState>()
    backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) {
        sut.uiState.collect { states.add(it) }
    }
    return sut to states
}

@Test
fun selectingGenre_loadsArtists() = runTest(UnconfinedTestDispatcher()) {
    val (sut, states) = createSut()
    sut.sendCommand(SelectGenre(rock))
    assertEquals(rock, states.last().selectedGenre)
}
```

**Почему `backgroundScope`:** `StateFlow.collect` никогда не возвращается. Запуск в собственном scope теста даёт `UncompletedCoroutinesError`. `backgroundScope` живёт рядом с тестом и автоматически отменяется по завершении.

**Почему нужен collector:** `WhileSubscribed` активирует upstream только пока кто-то подписан. Без коллектора `uiState.value` навсегда останется `Default`.

### `UnconfinedTestDispatcher` vs `StandardTestDispatcher`

- `Unconfined` — eager execution, синхронные на вид тесты. По умолчанию.
- `Standard` (дефолт `runTest`) — нужен `runCurrent()` после команд. Только для тестирования таймингов (debounce, delay).
- ⚠️ `advanceUntilIdle()` НЕ обрабатывает задачи `backgroundScope` — используйте `runCurrent()`.

### Fakes без mock-библиотек

```kotlin
// Lambda fake — простые случаи
val fakeArtists = GetArtistsForGenreUseCase { genreId ->
    when (genreId) {
        "rock" -> flowOf(rockArtists)
        else -> flowOf(persistentListOf())
    }
}

// Class fake — нужны call counts / захват параметров / push новых данных
class FakeGetArtistsForGenre : GetArtistsForGenreUseCase {
    var lastGenreId: String? = null
    var callCount = 0
    private val flow = MutableStateFlow<ImmutableList<Artist>>(persistentListOf())
    override fun invoke(genreId: String): Flow<ImmutableList<Artist>> {
        lastGenreId = genreId
        callCount++
        return flow
    }
    fun emit(items: ImmutableList<Artist>) { flow.value = items }
}
```

### Тестирование паттерна B (ViewStateDelegate)

```kotlin
@Test
fun `login sets isLoading true then false`() = runTest {
    viewModel.uiState.test {
        viewModel.onLoginClick()
        assertEquals(true, awaitItem().isLoading)
        assertEquals(false, awaitItem().isLoading)
    }
}
```

> `StateFlow` conflated — нет повторных эмиссий при том же значении. `states.size` НЕ является надёжным счётчиком команд.

---

## 10. KMP-СПЕЦИФИКА

- **Shared UIModels** — в `commonMain`. ZERO AndroidX imports.
- `expect`/`actual` — только для платформенных мостов (DataSource, Storage), НЕ для логики UIModel
- `StateFlow`/`Flow` из `kotlinx.coroutines.flow` — мультиплатформенны
- `kotlinx-serialization` для data моделей
- Repository в `commonMain` использует `expect`/`actual` для платформенного хранения (SQLDelight, Ktor)
- `android.content.Context`, UIKit-типы, `LiveData` **никогда** не попадают в `commonMain`

---

## 11. АНТИПАТТЕРНЫ — ЗАПРЕЩЕНО

| Антипаттерн | Почему |
|-------------|--------|
| MVI Reducer как основной паттерн | Лишний бойлерплейт без пользы |
| Логика внутри Android `ViewModel` (а не в UIModel) | Ломает KMP-портируемость |
| `CoroutineScope`, создаваемый внутри UIModel | Делает невозможной правильную привязку lifecycle и тесты |
| `stateIn(SharingStarted.Eagerly)` | Upstream в фоне — расход батареи; неверный момент `onStart` |
| Несколько `StateFlow` на экран | Несогласованные UI-состояния — используйте единый `UiState` |
| События для постоянного состояния | Пропуск событий при lifecycle — используйте поля `UiState` |
| Бизнес-логика в Composable | Не тестируемо, нарушает separation of concerns |
| `GlobalScope` в shared модулях | Неконтролируемый lifecycle, утечки |
| Platform APIs / `Context` / `LiveData` в `commonMain` | Ломает KMP |
| `Dispatchers.setMain()` / Robolectric / mock-либы в тестах UIModel | UIModel — чистый Kotlin, тестируется без Android |
| `TestScope` как scope для UIModel в тестах | Даёт `UncompletedCoroutinesError` — нужен `backgroundScope` |
| `ViewModel(viewModelScope) {}` без передачи UIModel.scope | Двойной lifecycle, утечка scope UIModel |

---

## 12. КОНТРОЛЬНЫЙ ЧЕКЛИСТ

```
Архитектура
□ UIModel в commonMain, 0 AndroidX imports
□ Android ViewModel — 3-строчный делегат через `by uiModel`
□ ViewModel(uiModel.scope) передан корректно (Lifecycle 2.8.0+)
□ CoroutineScope инжектируется, не создаётся внутри UIModel

Состояние
□ Один UiState (data class) на экран, с UIState.Default
□ isLoading и isError явно в UiState
□ Производные состояния вычислены в UIModel/ViewModel
□ Коллекции — ImmutableList (kotlinx.collections.immutable)

Реактивность (Паттерн A)
□ stateIn(WhileSubscribed(5_000), Default)
□ Каскадные зависимости через flatMapLatest
□ sendCommand сбрасывает downstream-выборы
□ Use cases — fun interface

Императив (Паттерн B)
□ reduce под Mutex (через ViewStateDelegate)
□ isLoading сбрасывается через invokeOnCompletion
□ Не смешан с реактивным паттерном A на одном экране

События
□ Разовые события через Channel, не SharedFlow
□ События только для навигации/toast/close
□ Сбор событий через LaunchedEffect

Compose
□ collectAsStateWithLifecycle() (или collectAsState() как fallback)
□ Composable получает uiState + лямбды (или onCommand), не ViewModel
□ Никакой бизнес-логики в Composable

Coroutines
□ Никакого GlobalScope
□ Никаких platform API в commonMain

Тесты
□ backgroundScope + UnconfinedTestDispatcher (НЕ TestScope, НЕ setMain)
□ Активный коллектор uiState (иначе WhileSubscribed не запустит upstream)
□ Fakes как fun interface lambdas или class fakes — без mock-либ
□ runCurrent() (не advanceUntilIdle()) для backgroundScope-задач

Запреты
□ MVI Reducer НЕ используется
□ LiveData в shared KMP НЕ используется
□ Eagerly в stateIn НЕ используется (только WhileSubscribed)
```

---

*Источники: [jamshidbekboynazarov — MVI Architecture Pattern](https://jamshidbekboynazarov.medium.com/mvi-architecture-pattern-in-android-with-jetpack-compose-0fd61f9c67fd), [MrAndroid — Android Architecture with MVVM and UiState](https://medium.com/@MrAndroid/android-architecture-with-mvvm-and-uistate-f29aa5494465), а также материал по UIModel + ViewModel separation для KMP/CMP.*

*Используйте вместе с `/clean-arch` для полного покрытия архитектурных правил.*
