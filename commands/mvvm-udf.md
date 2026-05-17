# MVVM + UDF Rules для KMP/CMP

You are an expert in MVVM + Unidirectional Data Flow (UDF) for Kotlin Multiplatform and Compose Multiplatform projects.

Apply ALL rules below when generating, reviewing, or refactoring code.

**Core pattern: MVVM + UDF. Do NOT use MVI** — no Reducer functions, no Intent/Effect sealed classes as primary pattern.

---

## 1. АРХИТЕКТУРНЫЕ СЛОИ

### Два верхнеуровневых слоя
- **Core (Data Layer)** — репозитории, remote/local DataSource, кэширование
- **UI Layer** — ViewModels, Composable screens, навигация

Для больших проектов добавляйте `uikit` (shared UI компоненты) и `tools` (утилиты) как отдельные модули. Не создавайте их спекулятивно для небольших приложений.

### Repository — единственный авторитет данных
Repository решает:
- откуда брать данные (remote API или локальный кэш)
- на каком coroutine dispatcher работать
- кэшировать ли и как долго

**Запрещено** принимать эти решения в ViewModel или UI.

---

## 2. ПРАВИЛА VIEWMODEL

### Один ViewModel на экран
ViewModel:
- хранит и управляет `UiState`
- экспонирует состояние как `StateFlow<UiState>`
- экспонирует разовые события через `Channel` / `Flow<Event>`
- **не содержит** View-ссылки, Context, платформо-специфичный UI код (важно для KMP)

### Шаблон структуры ViewModel

```kotlin
class LoginViewModel(
    private val authRepository: AuthRepository,
) : ViewModel(), ViewStateDelegate<UiState, Event> by ViewStateDelegateImpl(UiState()) {

    data class UiState(
        val isLoading: Boolean = false,
        val login: String = "",
        val password: String = "",
    )

    sealed interface Event {
        data object GoToHome : Event
    }

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

### KMP shared ViewModels
Используйте `kotlinx-coroutines` с общим `CoroutineScope` вместо `viewModelScope` на уровне shared модуля. Привязка к lifecycle делается на платформенной стороне (Android/iOS).

---

## 3. ПРАВИЛА UiState

### Один immutable state объект на экран
Всегда определяйте `UiState` как `data class` с дефолтными значениями. Никогда не рассыпайте состояние по нескольким `StateFlow` свойствам.

```kotlin
data class UiState(
    val isLoading: Boolean = false,
    val isError: Boolean = false,
    val items: List<ItemUiState> = emptyList(),
)
```

### State — read-only за пределами ViewModel
UI **никогда** не мутирует состояние напрямую. Единственная точка мутации — функция `reduce` внутри ViewModel.

### Явное моделирование loading и error
`UiState` ДОЛЖЕН содержать `isLoading` и `isError` (или `errorMessage: String?`). Никаких неявных состояний загрузки или исключений, утекающих в UI.

### Производные состояния — в UiState
Если отображение кнопки требует комбинации двух источников данных (`isLoggedIn && isPremium`) — вычислите это в ViewModel и выставьте как поле `UiState`, не сырые булевы для комбинирования в Composable.

---

## 4. ПАТТЕРН ViewStateDelegate

Используйте `ViewStateDelegate<UIState, Event>` для устранения бойлерплейта.

| Член | Тип | Назначение |
|------|-----|-----------|
| `uiState` | `Flow<UIState>` | Стрим состояния для UI |
| `stateValue` | `UIState` | Синхронное чтение текущего состояния |
| `singleEvents` | `Flow<Event>` | Стрим разовых событий |
| `reduce` | `suspend (UIState → UIState)` | Обновление состояния с Mutex |
| `asyncReduce` | `CoroutineScope.(UIState → UIState)` | Неблокирующее обновление |
| `sendEvent` | `suspend (Event)` | Отправка разового события |

Функция `reduce` ДОЛЖНА использовать `Mutex` для предотвращения конкурентной порчи состояния.

---

## 5. SINGLE LIVE EVENTS (разовые эффекты)

### Используйте Channel, не SharedFlow

```kotlin
private val singleEventsChannel = Channel<Event>(Channel.BUFFERED)
val singleEvents: Flow<Event> = singleEventsChannel.receiveAsFlow()
```

### События только для навигации и разовых UI-действий
События (single live events) — **только** для: навигации, показа snackbar/toast, закрытия экрана. Для постоянного UI состояния используйте поля `UiState`.

### Сбор событий с учётом lifecycle

```kotlin
LaunchedEffect(Unit) {
    viewModel.singleEvents.collect { event ->
        when (event) {
            is LoginViewModel.Event.GoToHome -> navController.navigate(...)
        }
    }
}
```

---

## 6. ПРАВИЛА COMPOSE UI (CMP)

### Экраны — stateless Composable
Composable-функции экранов получают `uiState` и колбэки, не ViewModel напрямую (кроме корневого уровня для связки).

### Сбор состояния с lifecycle safety

```kotlin
val uiState by viewModel.uiState.collectAsStateWithLifecycle()
```

На не-Android таргетах используйте `collectAsState()` до появления `collectAsStateWithLifecycle` для таргета.

### Никакой бизнес-логики в Composable
Composable только: рендерит состояние, передаёт жесты пользователя в функции ViewModel. Никакого `if/when` по сырым данным — готовые к отображению поля выводить в ViewModel.

### Передавайте отдельные лямбды, не весь ViewModel

```kotlin
// ПРАВИЛЬНО
LoginScreen(
    uiState = uiState,
    onLoginChange = viewModel::onLoginChange,
    onLoginClick = viewModel::onLoginClick,
)
// НЕПРАВИЛЬНО
LoginScreen(viewModel = viewModel)
```

---

## 7. COROUTINES И THREADING

- Весь async в `viewModelScope` (Android) или shared `CoroutineScope` (KMP)
- Repository функции — `suspend`, dispatcher-aware внутри
- Никогда не использовать `GlobalScope`
- Используйте `invokeOnCompletion` для сброса `isLoading` независимо от успеха/ошибки

---

## 8. АНТИПАТТЕРНЫ — ЗАПРЕЩЕНО

| Антипаттерн | Почему запрещено |
|-------------|-----------------|
| MVI Reducer как основной паттерн | Лишний бойлерплейт без пользы для большинства экранов |
| Несколько `StateFlow` на экран | Несогласованные UI состояния; используйте единый `UiState` |
| События для постоянного состояния | Пропущенные события при lifecycle; используйте поля `UiState` |
| Бизнес-логика в Composable | Не тестируемо, нарушает separation of concerns |
| `GlobalScope` в shared модулях | Неконтролируемый lifecycle, утечки памяти |
| Platform APIs в shared ViewModel | Ломает KMP-портируемость |
| `LiveData` в shared KMP модулях | Android-only, не мультиплатформенно |

---

## 9. KMP-СПЕЦИФИКА

- **Shared ViewModels** — в `commonMain`. `expect`/`actual` только для привязки к platform lifecycle
- `StateFlow` и `Flow` из `kotlinx.coroutines.flow` — мультиплатформенны, используйте их
- `kotlinx-serialization` для data моделей — мультиплатформенна по умолчанию
- Repository в `commonMain` использует `expect`/`actual` для platform-специфичного хранения (SQLDelight, Ktor)
- `android.content.Context` и UIKit-типы **никогда** не попадают в `commonMain`

---

## 10. ПРАВИЛА ТЕСТИРОВАНИЯ

- ViewModel логика тестируется unit-тестами: вызываем public функции, проверяем эмиссии `uiState`
- State-трансформации (`reduce`) тестируются через `Turbine` или `runTest` + `toList()`
- Repository мокируется через `FakeRepository` — реальная сеть в ViewModel-тестах никогда

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

---

## 11. КОНТРОЛЬНЫЙ ЧЕКЛИСТ

```
□ Один ViewModel на экран?
□ UiState — единый data class с дефолтными значениями?
□ isLoading и isError явно в UiState?
□ Производные состояния вычислены в ViewModel, не в Composable?
□ reduce защищён Mutex (через ViewStateDelegate)?
□ Разовые события через Channel, не SharedFlow?
□ События только для навигации/toast/close — не для постоянного состояния?
□ Composable получает uiState + лямбды, не ViewModel напрямую?
□ Никакого GlobalScope?
□ Никакого platform API в commonMain ViewModel?
□ isLoading сбрасывается через invokeOnCompletion?
□ MVI Reducer НЕ используется?
```

---

*Источники: [jamshidbekboynazarov — MVI Architecture Pattern](https://jamshidbekboynazarov.medium.com/mvi-architecture-pattern-in-android-with-jetpack-compose-0fd61f9c67fd) и [MrAndroid — Android Architecture with MVVM and UiState](https://medium.com/@MrAndroid/android-architecture-with-mvvm-and-uistate-f29aa5494465)*

*Используйте вместе с `/clean-arch` для полного покрытия архитектурных правил.*
