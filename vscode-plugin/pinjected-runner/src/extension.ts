// The module 'vscode' contains the VS Code extensibility API
// Import the module and reference it with the alias vscode in your code below
import * as vscode from 'vscode';
import * as path from 'path';

class RunButtonDecoration extends vscode.Disposable {
	private readonly decorationType: vscode.TextEditorDecorationType;

	constructor() {
		super(() => {
			this.decorationType.dispose();
		});
		console.log('RunButtonDecoration constructor');
		this.decorationType = vscode.window.createTextEditorDecorationType({
			gutterIconPath: vscode.Uri.file(path.join(__dirname, '..', 'resources', 'run.svg')),
			gutterIconSize: '90%',
		});
		console.log('RunButtonDecoration constructor end');
	}

	public updateDecorations(editor: vscode.TextEditor) {
		const decorations: vscode.DecorationOptions[] = [];
		console.log('RunButtonDecoration updateDecorations');

		for (let i = 0; i < editor.document.lineCount; i++) {
			const line = editor.document.lineAt(i);
			console.log('line:', line.text.trim());
			if (line.text.trim().includes(':IProxy')) {
				console.log('pushing decoration	to:', line.range);
				decorations.push({
					range: line.range,
					hoverMessage: 'Run this variable',
				});
			}
		}

		editor.setDecorations(this.decorationType, decorations);
	}
}

let runButtonDecoration: RunButtonDecoration;

export function activate(context: vscode.ExtensionContext) {
	runButtonDecoration = new RunButtonDecoration();
	console.log('RunButtonDecoration created');

	vscode.window.onDidChangeActiveTextEditor(
		(editor) => {
			if (editor) {
				console.log('update decoration');
				runButtonDecoration.updateDecorations(editor);
			}
		},
		null,
		context.subscriptions
	);

	vscode.workspace.onDidChangeTextDocument(
		(event) => {
			if (vscode.window.activeTextEditor && event.document === vscode.window.activeTextEditor.document) {
				runButtonDecoration.updateDecorations(vscode.window.activeTextEditor);
			}
		},
		null,
		context.subscriptions
	);

	const disposable = vscode.commands.registerCommand('pinjected-runner.run', () => {
		const editor = vscode.window.activeTextEditor;
		if (editor) {
			const document = editor.document;
			const selection = editor.selection;
			const varLine = document.lineAt(selection.active.line);
			const varText = varLine.text.trim();

			if (varText.includes(': pinjected.IProxy')) {
				const varName = varText.split(':')[0].trim();
				vscode.window.showInformationMessage(`Running variable: ${varName}`);
				// Execute the Python code to run the variable here
				// You can use the `varName` to identify the variable to run
			}
		}
	});

	context.subscriptions.push(disposable);
}

// This method is called when your extension is deactivated
export function deactivate() { }
