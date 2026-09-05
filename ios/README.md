# Audio Annotation iPhone App

This directory contains the first SwiftUI implementation of the Audio Playback and Annotation Recording app. It is intentionally small: it opens a local shared-plan folder, plays its WAV file, shows sentence context and timing, supports pause, ten-second navigation, playback rate selection, and opens recorded annotation timestamps.

The app does not perform text-to-speech or speech-to-text. The desktop application creates and updates the package files described in `.github/prompts/plan-audioAnnotationCli.prompt.md`.

## Requirements

- macOS with Xcode 15 or newer.
- An Apple ID. A free Apple ID can deploy to a personal iPhone for development, subject to Apple's provisioning limits.
- An iPhone running iOS 17 or newer for the current project settings.
- A physical USB cable or trusted Wi-Fi connection between the Mac and iPhone.

The repository currently has only Command Line Tools active in the development environment. Install and select the full Xcode application before building:

```sh
xcode-select --install
sudo xcode-select --switch /Applications/Xcode.app/Contents/Developer
xcodebuild -version
```

The first command is unnecessary when Command Line Tools are already installed; the second requires the full Xcode app to be installed.

## Build in Xcode

1. Open `ios/AudioAnnotation.xcodeproj` in Xcode.
2. Select the `AudioAnnotation` target and open **Signing & Capabilities**.
3. Select your Apple development team. Change the bundle identifier from `com.example.AudioAnnotation` to a unique identifier, such as `com.yourname.AudioAnnotation`.
4. Select an iPhone simulator or **Any iOS Device** as the run destination.
5. Use **Product > Build** (`Command-B`).
6. Select an iPhone simulator and use **Product > Run** (`Command-R`) for the first local test.

## Deploy to an iPhone as a Developer

1. Connect the iPhone to the Mac, unlock it, and choose **Trust** on the iPhone when prompted.
2. In Xcode, select the iPhone in the run-destination menu.
3. On the iPhone, enable **Settings > Privacy & Security > Developer Mode** if iOS requests it, then restart the phone.
4. In the target's **Signing & Capabilities**, select the same Apple ID/team and keep automatic signing enabled.
5. Press **Run**. Xcode creates a development-signed app and installs it on the phone.
6. The first launch may require **Settings > General > VPN & Device Management** and trusting the developer profile.
7. Grant microphone access when recording is implemented. The first-step build already includes the microphone usage description in `Info.plist`.

A free Apple ID generally requires periodically reinstalling the development build. A paid Apple Developer Program membership is needed for longer-lived provisioning, TestFlight, App Store distribution, and some device capabilities.

## Open a Plan Package

Use **Open Plan** in the app and select a local or iCloud Drive folder containing at least:

```text
plan.timing.json
plan.wav
annotations.json  (optional for the first playback build)
```

The manifest's `audio_file` path is resolved relative to the selected folder. The current prototype reads the manifest and annotation files and plays the plan WAV locally. Annotation audio playback expects a path supplied by the package; recording and reply creation are planned for the next implementation step.

## Command-Line Build

After installing full Xcode and selecting its developer directory:

```sh
xcodebuild \
  -project ios/AudioAnnotation.xcodeproj \
  -scheme AudioAnnotation \
  -sdk iphonesimulator \
  -configuration Debug \
  -derivedDataPath .build/AudioAnnotation build
```

For a physical device, select a connected destination shown by:

```sh
xcodebuild -project ios/AudioAnnotation.xcodeproj -scheme AudioAnnotation -showdestinations
```

A physical-device build needs a valid signing team. Xcode's GUI is recommended for the first signing setup.

## Current Scope

This first step does not yet record microphone audio, write annotation JSON, synchronize packages, or merge annotation replies. Those features remain governed by the two application plans and will be added after the local playback slice is verified on a device.
