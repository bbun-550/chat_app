import SwiftUI

#if os(iOS)
@main
struct OpenClawIOSApp: App {
    var body: some Scene {
        WindowGroup {
            TabView {
                Tab("Chats", systemImage: "bubble.left.and.bubble.right") {
                    ChatListView()
                }

                Tab("Settings", systemImage: "gear") {
                    NavigationStack {
                        iOSSettingsView()
                    }
                }
            }
        }
    }
}
#endif
