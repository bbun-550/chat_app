import SwiftUI

struct iOSSettingsView: View {
    @StateObject private var vm = SettingsViewModel()

    var body: some View {
        Form {
            Section("Server") {
                TextField("Base URL", text: $vm.serverURLText)
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
                Button {
                    vm.saveServerURL()
                } label: {
                    HStack {
                        Text("Save")
                        Spacer()
                        if vm.showSaveConfirmation {
                            Image(systemName: "checkmark.circle.fill")
                                .foregroundStyle(.green)
                                .transition(.scale.combined(with: .opacity))
                        }
                    }
                }
                .animation(.easeInOut, value: vm.showSaveConfirmation)

                Button {
                    vm.resetServerURL()
                } label: {
                    HStack {
                        Text("Reset")
                        Spacer()
                        if vm.showResetConfirmation {
                            Image(systemName: "checkmark.circle.fill")
                                .foregroundStyle(.green)
                                .transition(.scale.combined(with: .opacity))
                        }
                    }
                }
                .animation(.easeInOut, value: vm.showResetConfirmation)
            }
            if let error = vm.errorMessage {
                Section {
                    Text(error).foregroundStyle(.red)
                }
            }
        }
        .navigationTitle("Settings")
        #if os(iOS)
        .navigationBarTitleDisplayMode(.inline)
        #endif
    }
}
