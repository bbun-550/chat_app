import SwiftUI

struct iOSSettingsView: View {
    @StateObject private var vm = SettingsViewModel()

    var body: some View {
        Form {
            Section("Server") {
                TextField("Base URL", text: $vm.serverURLText)
                TextField("API Token (optional)", text: $vm.apiToken)
                Button("Save") {
                    vm.saveServerURL()
                }
                Button("Reset") {
                    vm.resetServerURL()
                }
            }
            if let error = vm.errorMessage {
                Section {
                    Text(error).foregroundStyle(.red)
                }
            }
        }
        .navigationTitle("Settings")
    }
}
