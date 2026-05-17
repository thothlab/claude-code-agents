# CLEAN Architecture — Android / KMP / CMP

You are an expert in Clean Architecture for Android, Kotlin Multiplatform (KMP), and Compose Multiplatform (CMP).

Apply ALL rules below when generating, reviewing, or refactoring code. Never violate layer boundaries or dependency directions.

---

## 1. СЛОИ И ОТВЕТСТВЕННОСТЬ

### Presentation Layer
- UI: Composable / Screen / Fragment
- State: ViewModel, UIState, UIModel
- Mapping: Domain → UIModel (только здесь)
- **Запрещено:** DTO, Entity, бизнес-логика, маппинг DTO→Domain

### Domain Layer
- UseCase, Domain Models, Repository интерфейсы
- Трансформации Domain → Domain
- **Запрещено:** DTO, Entity, UIModel, реализации репозиториев

### Data Layer
- Repository реализации, Remote/Local DataSource
- DTO, Entity (Room / SQLDelight), Mappers DTO/Entity → Domain
- **Запрещено:** UIModel, бизнес-логика

---

## 2. НАПРАВЛЕНИЕ ЗАВИСИМОСТЕЙ

```
Presentation → Domain ← Data
```

- Domain не зависит ни от чего
- Presentation не зависит от Data напрямую

---

## 3. ПРАВИЛА МАППИНГА

```
Data:         DTO/Entity → Domain   (fun UserDTO.toDomain(): UserDomain)
Presentation: Domain → UIModel      (fun UserDomain.toUIModel(): UserUIModel)
Domain:       Domain → Domain       (трансформации, не "mapper")
```

**Запрещено:**
- DTO в Presentation
- UIModel из UseCase
- Entity в ViewModel

---

## 4. НОМЕНКЛАТУРА МОДЕЛЕЙ

| Суффикс | Слой | Пример |
|---------|------|--------|
| DTO / Response | Data (API) | UserDTO |
| Entity | Data (DB) | UserEntity |
| (Domain) / Domain | Domain | User, UserDomain |
| UIModel / UIState | Presentation | UserUIModel |

---

## 5. ПРАВИЛА UseCase

Используйте когда:
- Логика переиспользуется несколькими ViewModel
- Логика координирует несколько репозиториев
- Нужно отдельное тестирование

Пропустите, если: простой прямой вызов одного репозитория без логики.

```kotlin
class GetUserUseCase(private val repo: UserRepository) {
    suspend operator fun invoke(id: String): UserDomain = repo.getUser(id)
}
```

---

## 6. ПРАВИЛА РЕПОЗИТОРИЕВ

- Интерфейс в Domain, реализация в Data
- Оперируют только Domain моделями
- Координируют Remote + Local DataSource
- Даже без интерфейса — это **Data слой**

---

## 7. KMP-СПЕЦИФИЧНЫЕ ПРАВИЛА

### Структура модулей KMP

```
shared/
├── commonMain/
│   ├── domain/
│   │   ├── model/          # Domain модели — чистый Kotlin
│   │   ├── usecase/        # UseCases — чистый Kotlin
│   │   └── repository/     # Repository интерфейсы
│   └── data/
│       ├── repository/     # Реализации (если платформонезависимые)
│       ├── remote/         # Ktor клиенты (multiplatform)
│       └── local/          # SQLDelight (multiplatform)
├── androidMain/
│   └── data/local/         # Room или Android SharedPreferences
└── iosMain/
    └── data/local/         # NSUserDefaults, iOS-специфика

androidApp/                 # Android Presentation layer
iosApp/                     # iOS (SwiftUI или CMP)
composeApp/                 # CMP Presentation layer
```

### expect/actual

```kotlin
// commonMain — интерфейс поведения
expect class DatabaseDriver {
    fun create(): SqlDriver
}

// androidMain
actual class DatabaseDriver(private val context: Context) {
    actual fun create() = AndroidSqliteDriver(...)
}

// iosMain
actual class DatabaseDriver {
    actual fun create() = NativeSqliteDriver(...)
}
```

**Правило:** `expect`/`actual` только для DataSource и платформенных утилит. Domain и UseCase — только `commonMain`, никаких `expect`/`actual`.

### Что куда идёт в KMP

| Компонент | Где |
|-----------|-----|
| Domain Models | `commonMain/domain/model/` |
| UseCase | `commonMain/domain/usecase/` |
| Repository интерфейс | `commonMain/domain/repository/` |
| Repository реализация | `commonMain/data/` или `*Main/data/` |
| Ktor API клиент | `commonMain/data/remote/` |
| SQLDelight DAO | `commonMain/data/local/` |
| Room DAO | `androidMain/data/local/` |
| ViewModel | `commonMain/presentation/` (через lifecycle-viewmodel-compose) |
| Composables | `composeApp/commonMain/` или `*Main/` |

### Зависимости KMP Data слоя

```kotlin
// Предпочитайте мультиплатформенные решения:
// Networking:  Ktor (не Retrofit)
// DB:          SQLDelight (не Room в shared)
// Prefs:       MultiplatformSettings
// DI:          Koin (мультиплатформенный)
// Async:       Kotlin Coroutines + Flow
```

### Repository без платформенной логики — в commonMain

```kotlin
// commonMain — если нет платформоспецифики
class UserRepositoryImpl(
    private val api: UserApi,      // Ktor — multiplatform
    private val db: UserLocalDataSource  // SQLDelight — multiplatform
) : UserRepository {
    override suspend fun getUser(id: String): UserDomain {
        return db.getUser(id)?.toDomain() ?: api.getUser(id).toDomain()
    }
}
```

---

## 8. CMP-СПЕЦИФИЧНЫЕ ПРАВИЛА

### Структура composeApp

```
composeApp/
├── commonMain/
│   └── presentation/
│       ├── screens/       # Shared Composables (большинство экранов)
│       ├── components/    # UI компоненты
│       ├── navigation/    # NavHost / Decompose / Voyager
│       └── theme/         # MaterialTheme, Typography
├── androidMain/
│   └── presentation/      # Android-специфичные composables (редко)
└── iosMain/
    └── presentation/      # iOS-специфичные composables (редко)
```

### Навигация в CMP

**Предпочитайте:**
- Decompose — лучшая поддержка многоплатформенной навигации с back stack
- Voyager — проще, хорошо для большинства проектов
- Navigation Compose (Jetpack) — только если проект Android-first с CMP UI

```kotlin
// Voyager пример
class ProfileScreen : Screen {
    @Composable
    override fun Content() {
        val viewModel = getScreenModel<ProfileViewModel>()
        ProfileContent(state = viewModel.state)
    }
}
```

### ViewModel в CMP

```kotlin
// commonMain — используйте lifecycle-viewmodel от JetBrains
// Gradle: implementation("org.jetbrains.androidx.lifecycle:lifecycle-viewmodel-compose:...")

class ProfileViewModel : ViewModel() {
    private val _state = MutableStateFlow(ProfileUIState())
    val state: StateFlow<ProfileUIState> = _state.asStateFlow()
}
```

**Правило:** ViewModel в `commonMain` — не дублируйте для каждой платформы.

### Платформоспецифичный UI — только когда необходимо

```kotlin
// Предпочитайте общий commonMain composable
@Composable
fun CameraPermissionButton(onGranted: () -> Unit) {
    // commonMain: используйте Moko Permissions или аналог
}

// Только если нет мультиплатформенного решения:
// androidMain — используйте ActivityResultContracts
// iosMain    — используйте AVFoundation через interop
```

### Что делать с iOS-специфичным UI

```kotlin
// Вариант 1: UIKitView в CMP для нативных iOS компонентов
@Composable
actual fun NativeMapView() {
    UIKitView(factory = { MKMapView() })
}

// Вариант 2: expect/actual для платформенных компонентов
@Composable
expect fun PlatformDatePicker(onDateSelected: (Long) -> Unit)
```

---

## 9. DEPENDENCY INJECTION В KMP

### Koin (рекомендуется для KMP)

```kotlin
// commonMain — shared модули
val domainModule = module {
    factory { GetUserUseCase(get()) }
    factory { GetProfileSummaryUseCase(get()) }
}

val dataModule = module {
    single<UserRepository> { UserRepositoryImpl(get(), get()) }
    single { UserApi(get()) }        // Ktor HttpClient
}

// androidMain — платформенные зависимости
val androidDataModule = module {
    single { UserLocalDataSource(get()) }   // Room
    single { createAndroidDatabaseDriver(get()) }
}

// iosMain
val iosDataModule = module {
    single { UserLocalDataSource(get()) }   // SQLDelight Native
    single { createIOSDatabaseDriver() }
}
```

---

## 10. КОНТРОЛЬНЫЙ ЧЕКЛИСТ (Android + KMP + CMP)

```
□ Domain слой — чистый Kotlin, только в commonMain, 0 платформозависимостей?
□ UseCase возвращают Domain модели (не UIModel, не DTO)?
□ Repository интерфейсы в Domain, реализации в Data?
□ DTO/Entity не выходят за границы Data слоя?
□ Маппинги Domain→UI только в Presentation слое?
□ ViewModel в commonMain (lifecycle-viewmodel)?
□ Networking через Ktor (не Retrofit) в shared?
□ БД через SQLDelight (не Room) в shared?
□ expect/actual только для DataSource/утилит, не для Domain?
□ Навигация через Decompose/Voyager (не платформоспецифично)?
□ Платформоспецифичный UI только при отсутствии мультиплатформенного решения?
□ DI через Koin с отдельными модулями для каждой платформы?
```

---

## 11. ТИПИЧНЫЕ ОШИБКИ KMP/CMP

| Ошибка | Неправильно | Правильно |
|--------|-------------|-----------|
| Domain в androidMain | `androidMain/domain/` | `commonMain/domain/` |
| Retrofit в shared | `implementation("retrofit2:...")` в commonMain | Ktor в commonMain |
| Room в shared | `commonMain/data/local/Room` | SQLDelight в commonMain |
| ViewModel дублирование | Отдельный VM для Android и iOS | Один VM в commonMain |
| expect/actual для UseCase | `expect class GetUserUseCase` | Только в commonMain, без expect |
| Platform logic в Domain | `if (Platform.isAndroid)` в UseCase | expect/actual в Data слое |

---

## 12. ЭТАЛОННЫЙ ПРИМЕР KMP + CMP

```kotlin
// ===== commonMain/domain/model/ =====
data class UserDomain(val id: String, val fullName: String, val isPremium: Boolean)

// ===== commonMain/domain/repository/ =====
interface UserRepository {
    suspend fun getUser(id: String): UserDomain
    fun observeUser(id: String): Flow<UserDomain>
}

// ===== commonMain/domain/usecase/ =====
class GetProfileSummaryUseCase(private val repo: UserRepository) {
    suspend operator fun invoke(id: String): ProfileSummary {
        val user = repo.getUser(id)
        return ProfileSummary(fullName = user.fullName, canAccessPremium = user.isPremium)
    }
}

// ===== commonMain/data/remote/ =====
data class UserDTO(val id: String, val first_name: String, val last_name: String, val premium: Boolean)
fun UserDTO.toDomain() = UserDomain(id, "$first_name $last_name", premium)

// ===== commonMain/data/repository/ =====
class UserRepositoryImpl(private val api: UserApi, private val db: UserLocalDataSource) : UserRepository {
    override suspend fun getUser(id: String): UserDomain =
        db.getUser(id)?.toDomain() ?: api.getUser(id).also { db.saveUser(it) }.toDomain()

    override fun observeUser(id: String): Flow<UserDomain> =
        db.observeUser(id).map { it.toDomain() }
}

// ===== commonMain/presentation/ =====
data class ProfileUIState(val displayName: String = "", val isPremium: Boolean = false)
fun ProfileSummary.toUIState() = ProfileUIState(displayName = fullName, isPremium = canAccessPremium)

class ProfileViewModel(private val getProfile: GetProfileSummaryUseCase) : ViewModel() {
    private val _state = MutableStateFlow(ProfileUIState())
    val state: StateFlow<ProfileUIState> = _state.asStateFlow()

    fun load(userId: String) {
        viewModelScope.launch {
            _state.value = getProfile(userId).toUIState()
        }
    }
}

// ===== composeApp/commonMain/screens/ =====
@Composable
fun ProfileScreen(viewModel: ProfileViewModel = koinViewModel()) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    ProfileContent(state = state)
}
```

---

*Источник правил Android: https://oleksii-tym.medium.com/clean-architecture-in-android-a-practical-way-to-think-about-layers-mappers-dependencies-and-ad59c67e4601*
