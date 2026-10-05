# JARVIS-X Mobile Companion (Android App)

Dedicated permission-based execution companion application for **iQOO Neo 10R** and modern Android devices.

## Build & Setup Instructions

### 1. Requirements & Java Setup
- **Android Studio**: Jellyfish | Koala or newer
- **Android SDK**: API 34 (Android 14)
- **Kotlin**: 1.9.20+
- **JDK 17**: 
  - If using **Android Studio**, export Android Studio's bundled JDK:
    ```bash
    export JAVA_HOME="/Applications/Android Studio.app/Contents/jbr/Contents/Home"
    ```
  - Or set system Java 17 via Homebrew:
    ```bash
    export JAVA_HOME=$(/usr/libexec/java_home -v 17)
    ```

### 2. Building Debug & Release APK
Open terminal inside `jarvis-x-mobile/` directory:

#### Debug APK Build:
```bash
export JAVA_HOME="/Applications/Android Studio.app/Contents/jbr/Contents/Home"
./gradlew assembleDebug
```
The output APK will be generated at:
`app/build/outputs/apk/debug/app-debug.apk`

#### Release APK Build:
```bash
./gradlew assembleRelease
```
The output APK will be generated at:
`app/build/outputs/apk/release/app-release.apk`

---

### 3. Quick Setup Workflow
1. Open project in **Android Studio** (`Open -> jarvis-x-mobile`).
2. Run **Gradle Sync**.
3. Connect your **iQOO Neo 10R** via USB Debugging.
4. Click **Run App (Shift + F10)** or install generated `app-debug.apk`.
5. Open **JARVIS-X Mobile** on the phone.
6. Open **JARVIS-X Settings -> Devices -> Phone** on Laptop.
7. Scan QR Code to establish secure session token pairing.
8. Grant requested Android permissions:
   - `CALL_PHONE`
   - `READ_CONTACTS`
   - `POST_NOTIFICATIONS`
   - `RECORD_AUDIO`
9. Test voice commands:
   - *"Jarvis, is my phone connected?"*
   - *"Jarvis, call Shyam."*
