import SwiftUI

struct MacSettingsView: View {
    @StateObject private var vm = SettingsViewModel()

    var body: some View {
        Form {
            TextField("Base URL", text: $vm.serverURLText)
            TextField("API Token (optional)", text: $vm.apiToken)
            HStack {
                Button("Save") {
                    vm.saveServerURL()
                }
                Button("Reset") {
                    vm.resetServerURL()
                }
            }
            if let error = vm.errorMessage {
                Text(error).foregroundStyle(.red)
            }
        }
        .padding()
        .frame(minWidth: 420, minHeight: 180)
    }
}
