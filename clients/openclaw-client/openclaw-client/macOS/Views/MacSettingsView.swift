import SwiftUI

struct MacSettingsView: View {
    @StateObject private var vm = SettingsViewModel()

    var body: some View {
        Form {
            TextField("Base URL", text: $vm.serverURLText)
                .autocorrectionDisabled()
                .accessibilityLabel("Base URL")
            HStack {
                if vm.isTokenVisible {
                    TextField("API Token (optional)", text: $vm.apiToken)
                        .textContentType(.password)
                } else {
                    SecureField("API Token (optional)", text: $vm.apiToken)
                        .textContentType(.password)
                }
                Button {
                    vm.isTokenVisible.toggle()
                } label: {
                    Image(systemName: vm.isTokenVisible ? "eye" : "eye.slash")
                        .foregroundStyle(.secondary)
                }
                .buttonStyle(.plain)
                .accessibilityLabel(vm.isTokenVisible ? "Hide API token" : "Show API token")
            }
            HStack {
                Button {
                    vm.saveServerURL()
                } label: {
                    HStack(spacing: 4) {
                        Text("Save")
                        if vm.showSaveConfirmation {
                            Image(systemName: "checkmark.circle.fill")
                                .foregroundStyle(.green)
                                .transition(.scale.combined(with: .opacity))
                        }
                    }
                    .animation(.easeInOut, value: vm.showSaveConfirmation)
                }
                .keyboardShortcut(.defaultAction)
                Button {
                    vm.resetServerURL()
                } label: {
                    HStack(spacing: 4) {
                        Text("Reset")
                        if vm.showResetConfirmation {
                            Image(systemName: "checkmark.circle.fill")
                                .foregroundStyle(.green)
                                .transition(.scale.combined(with: .opacity))
                        }
                    }
                    .animation(.easeInOut, value: vm.showResetConfirmation)
                }
            }
            if let error = vm.errorMessage {
                Text(error).foregroundStyle(.red)
            }
        }
        .padding()
        .frame(minWidth: 420, minHeight: 160)
    }
}
