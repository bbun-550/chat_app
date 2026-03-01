import SwiftUI

struct MacSettingsView: View {
    @StateObject private var vm = SettingsViewModel()

    var body: some View {
        Form {
            TextField("Base URL", text: $vm.serverURLText)
                .autocorrectionDisabled()
                .accessibilityLabel("Base URL")
            HStack {
                Button("Save") {
                    vm.saveServerURL()
                }
                .keyboardShortcut(.defaultAction)
                Button("Reset") {
                    vm.resetServerURL()
                }
            }
            if let error = vm.errorMessage {
                Text(error).foregroundStyle(.red)
            }
        }
        .padding()
        .frame(minWidth: 420, minHeight: 140)
    }
}
