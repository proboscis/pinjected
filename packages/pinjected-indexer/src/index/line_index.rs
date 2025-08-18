use rustpython_ast::text_size::TextSize;

/// Helper to convert TextSize to line numbers
pub struct LineIndex {
    line_starts: Vec<TextSize>,
}

impl LineIndex {
    /// Create a new LineIndex from source text
    pub fn new(source: &str) -> Self {
        let mut line_starts = vec![TextSize::from(0)];
        for (i, ch) in source.char_indices() {
            if ch == '\n' {
                line_starts.push(TextSize::from((i + 1) as u32));
            }
        }
        Self { line_starts }
    }
    
    /// Get line number (1-based) for a TextSize offset
    pub fn line_number(&self, offset: TextSize) -> usize {
        self.line_starts
            .binary_search(&offset)
            .unwrap_or_else(|i| i.saturating_sub(1)) + 1
    }
}