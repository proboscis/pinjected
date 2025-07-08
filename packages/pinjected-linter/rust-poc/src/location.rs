/// Module for converting byte offsets to line:column positions
use std::sync::Arc;

#[derive(Debug, Clone)]
pub struct LineIndex {
    /// Source code
    source: Arc<str>,
    /// Byte offset of each line start
    line_starts: Vec<usize>,
}

impl LineIndex {
    pub fn new(source: impl Into<Arc<str>>) -> Self {
        let source = source.into();
        let mut line_starts = vec![0];

        for (i, ch) in source.char_indices() {
            if ch == '\n' {
                line_starts.push(i + 1);
            }
        }

        Self {
            source,
            line_starts,
        }
    }

    /// Convert byte offset to 1-based line and column
    pub fn get_location(&self, offset: usize) -> (usize, usize) {
        let line = match self.line_starts.binary_search(&offset) {
            Ok(line) => line,
            Err(line) => line.saturating_sub(1),
        };

        let line_start = self.line_starts[line];
        let column = self.source[line_start..offset].chars().count();

        (line + 1, column + 1) // 1-based
    }
}
