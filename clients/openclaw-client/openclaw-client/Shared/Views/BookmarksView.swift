import SwiftUI

struct BookmarksView: View {
    @State private var bookmarks: [Message] = []
    @State private var isLoading = false
    @State private var errorMessage: String?

    var body: some View {
        NavigationStack {
            Group {
                if isLoading {
                    ProgressView()
                } else if bookmarks.isEmpty {
                    ContentUnavailableView(
                        "북마크 없음",
                        systemImage: "bookmark",
                        description: Text("메시지를 길게 눌러 북마크를 추가하세요")
                    )
                } else {
                    List(bookmarks) { message in
                        BookmarkRowView(message: message) {
                            Task { await toggleBookmark(message) }
                        }
                    }
                    .listStyle(.plain)
                }
            }
            .navigationTitle("북마크")
            #if os(iOS)
            .navigationBarTitleDisplayMode(.large)
            #endif
            .task { await loadBookmarks() }
            .refreshable { await loadBookmarks() }
            .alert("Error", isPresented: Binding(
                get: { errorMessage != nil },
                set: { _ in errorMessage = nil }
            )) {
                Button("OK", role: .cancel) {}
            } message: {
                Text(errorMessage ?? "")
            }
        }
    }

    private func loadBookmarks() async {
        isLoading = true
        defer { isLoading = false }
        do {
            bookmarks = try await APIClient.shared.fetchBookmarks()
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    private func toggleBookmark(_ message: Message) async {
        do {
            _ = try await APIClient.shared.toggleBookmark(messageId: message.id)
            await loadBookmarks()
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}

private struct BookmarkRowView: View {
    let message: Message
    var onRemove: () -> Void
    @State private var isExpanded = false

    var body: some View {
        DisclosureGroup(isExpanded: $isExpanded) {
            MarkdownContentView(text: message.content)
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(.top, 4)
        } label: {
            VStack(alignment: .leading, spacing: 4) {
                HStack {
                    Label(
                        message.role == "user" ? "You" : "Assistant",
                        systemImage: message.role == "user" ? "person.fill" : "sparkles"
                    )
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    Spacer()
                    Text(message.created_at.prefix(10))
                        .font(.caption2)
                        .foregroundStyle(.tertiary)
                }
                if !isExpanded {
                    Text(message.content)
                        .lineLimit(2)
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }
            }
        }
        .padding(.vertical, 4)
        .swipeActions(edge: .trailing, allowsFullSwipe: true) {
            Button(role: .destructive, action: onRemove) {
                Label("북마크 해제", systemImage: "bookmark.slash")
            }
        }
    }
}
