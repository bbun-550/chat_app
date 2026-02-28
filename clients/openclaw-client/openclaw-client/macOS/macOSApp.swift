import SwiftUI

#if os(macOS)
@main
struct OpenClawMacApp: App {
    var body: some Scene {
        WindowGroup {
            ChatSplitView()
        }

        Settings {
            MacSettingsView()
        }
    }
}
#endif
