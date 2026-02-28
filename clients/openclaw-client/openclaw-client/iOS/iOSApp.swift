import SwiftUI

#if os(iOS)
@main
struct OpenClawIOSApp: App {
    var body: some Scene {
        WindowGroup {
            TabView {
                ChatListView()
                    .tabItem {
                        Label("Chats", systemImage: "bubble.left.and.bubble.right")
                    }

                NavigationStack {
                    iOSSettingsView()
                }
                .tabItem {
                    Label("Settings", systemImage: "gear")
                }
            }
        }
    }
}
#endif
