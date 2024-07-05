"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || function (mod) {
    if (mod && mod.__esModule) return mod;
    var result = {};
    if (mod != null) for (var k in mod) if (k !== "default" && Object.prototype.hasOwnProperty.call(mod, k)) __createBinding(result, mod, k);
    __setModuleDefault(result, mod);
    return result;
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.activate = activate;
exports.deactivate = deactivate;
// The module 'vscode' contains the VS Code extensibility API
// Import the module and reference it with the alias vscode in your code below
const vscode = __importStar(require("vscode"));
const path = __importStar(require("path"));
class RunButtonDecoration extends vscode.Disposable {
    decorationType;
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
    updateDecorations(editor) {
        const decorations = [];
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
let runButtonDecoration;
function activate(context) {
    runButtonDecoration = new RunButtonDecoration();
    console.log('RunButtonDecoration created');
    vscode.window.onDidChangeActiveTextEditor((editor) => {
        if (editor) {
            console.log('update decoration');
            runButtonDecoration.updateDecorations(editor);
        }
    }, null, context.subscriptions);
    vscode.workspace.onDidChangeTextDocument((event) => {
        if (vscode.window.activeTextEditor && event.document === vscode.window.activeTextEditor.document) {
            runButtonDecoration.updateDecorations(vscode.window.activeTextEditor);
        }
    }, null, context.subscriptions);
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
function deactivate() { }
//# sourceMappingURL=extension.js.map