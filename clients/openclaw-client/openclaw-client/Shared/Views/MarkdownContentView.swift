import SwiftUI
import MarkdownUI

struct MarkdownContentView: View {
    let text: String

    var body: some View {
        Markdown(text)
            .markdownTheme(.gitHub)
            .textSelection(.enabled)
    }
}
