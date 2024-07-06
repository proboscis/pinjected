// The module 'vscode' contains the VS Code extensibility API
// Import the module and reference it with the alias vscode in your code below
import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import * as cp from 'child_process';

const runConfigCache: { [filename: string]: { [varname: string]: RunConfig[] } } = {};

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

interface RunConfig {
	name: string;
	script_path: string;
	interpreter_path: string;
	arguments: string[];
	working_dir: string;
}

interface PinjectedOutput {
	configs: {
		[varName: string]: RunConfig[];
	};
}

async function getPythonPath(): Promise<string | undefined> {
	const pythonExtension = vscode.extensions.getExtension('ms-python.python');
	if (pythonExtension) {
		const pythonApi = await pythonExtension.activate();
		return pythonApi.settings.getExecutionDetails().execCommand;
	}
	return undefined;
}

function ensureLaunchJsonExists() {
	const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
	if (!workspaceFolder) {
		vscode.window.showErrorMessage('No workspace folder found. Please open a workspace folder and try again.');
		return;
	}

	const launchJsonPath = path.join(workspaceFolder.uri.fsPath, '.vscode', 'launch.json');
	// make .vscode folder if not exists
	if (!fs.existsSync(path.join(workspaceFolder.uri.fsPath, '.vscode'))) {
		fs.mkdirSync(path.join(workspaceFolder.uri.fsPath, '.vscode'));
	}
	// make launch.json if not exists
	if (!fs.existsSync(launchJsonPath)) {
		fs.writeFileSync(launchJsonPath, JSON.stringify({ version: '0.2.0', configurations: [] }, null, 2), 'utf8');
	}
}


async function getPinjectedPath(): Promise<string> {
	const python_path = await getPythonPath();
	const pinjectedPath = cp.execSync(`${python_path} -c "import pinjected; print(pinjected.__file__)"`, { encoding: 'utf8' }).trim();
	const pinjectedPackagePath = pinjectedPath.replace("__init__.py", "");
	return pinjectedPackagePath;
}

async function registerDebugConfiguration(runConfig: RunConfig, varName: string) {
	const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
	if (!workspaceFolder) {
		vscode.window.showErrorMessage('No workspace folder found. Please open a workspace folder and try again.');
		return;
	}

	const launchJsonPath = path.join(workspaceFolder.uri.fsPath, '.vscode', 'launch.json');
	ensureLaunchJsonExists();
	/**
	 * For debugpy, you need to specify the path of a script, rather than a module with -m.
	 * So, we need to convert -m pinjected run into
	 * site-packages/pinjected/main.py run <var_path> <design_path>
	 * For that you need to first check where 'pinjected' is installed.
	 * 
	 */
	const launchConfig = {
		type: 'debugpy',
		request: 'launch',
		name: `Debug ${varName}`,
		//program: runConfig.interpreter_path,
		program:(await getPinjectedPath())+"__main__.py",
		args: ["run",...runConfig.arguments.slice(2)],
		env: {},
	};

	let launchConfigurations: any[] = [];
	if (fs.existsSync(launchJsonPath)) {
		const launchJsonContent = fs.readFileSync(launchJsonPath, 'utf8');
		const launchJson = JSON.parse(launchJsonContent);
		launchConfigurations = launchJson.configurations || [];
	}

	// replace a configuration with the same name
	const existingConfigIndex = launchConfigurations.findIndex((config) => config.name === launchConfig.name);
	if (existingConfigIndex !== -1) {
		launchConfigurations[existingConfigIndex] = launchConfig;
	} else {
		//add a new configuration if not found
		launchConfigurations.push(launchConfig);
	}

	const updatedLaunchJson = {
		version: '0.2.0',
		configurations: launchConfigurations,
	};

	fs.writeFileSync(launchJsonPath, JSON.stringify(updatedLaunchJson, null, 2), 'utf8');
}
async function runVariable(varName: string) {
	vscode.window.showInformationMessage(`Running variable: ${varName}`);
	/**
	 * - get the open file path
	 * - check cache for file_path.varName
	 * - if not found,
	 * 0. get the python binary path
	 * 1. get the run config data by running pinjected module.
	 *   - `python -m pinjected --run-config file_path`
	 *   - parse the stdout as json.
	 * 2. register to the cache
	 * 3. register it to launch.json or anything to support running with debugger
	 */
	const editor = vscode.window.activeTextEditor;
	if (editor){
		const doc = editor.document;
		const filePath = doc.uri.fsPath;
		const runConfigs = await getRunConfigs(filePath, varName);
		if (runConfigs) {
			vscode.window.showInformationMessage(`Running variable: ${varName}`);
			const runConfig: RunConfig = runConfigs[0];
			await registerDebugConfiguration(runConfig, varName);
			const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
			vscode.debug.startDebugging(workspaceFolder, `Debug ${varName}`);
		}
	}
}
function extractPinjectedJson(text: string): PinjectedOutput {
	const pinjectedRegex = /<pinjected>(.*?)<\/pinjected>/s;
	const match = text.match(pinjectedRegex);

	if (match && match[1]) {
		try {
			return JSON.parse(match[1]) as PinjectedOutput;
		} catch (error) {
			vscode.window.showErrorMessage(`Failed to parse pinjected JSON. Error: ${error} `);
			throw error;
		}
	}
	vscode.window.showErrorMessage(`Failed to parse pinjected JSON. Error, no match found.`);
	throw new Error('Failed to extract pinjected JSON');
}


async function getRunConfigs(filePath: string, varName: string): Promise<RunConfig[]> {
	const python_path = await getPythonPath();
	const cacheKey = `${filePath}`;
	if (cacheKey in runConfigCache && varName in runConfigCache[cacheKey]) {
		return runConfigCache[cacheKey][varName];
	} else {

		try {
			const result = cp.execSync(`${python_path} -m pinjected.meta_main pinjected.ide_supports.create_configs.create_idea_configurations "${filePath}"`, { encoding: 'utf8' });

			const pinjectedOutput: PinjectedOutput = extractPinjectedJson(result);

			runConfigCache[cacheKey] = pinjectedOutput.configs;
		} catch (error) {
			vscode.window.showErrorMessage(`Failed to get run configuration for variable ${varName}. Error: ${error}`);
		}
		return runConfigCache[cacheKey][varName];
	}
}

export function activate(context: vscode.ExtensionContext) {
	runButtonDecoration = new RunButtonDecoration();

	vscode.window.onDidChangeActiveTextEditor(
		(editor) => {
			if (editor) {
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

	context.subscriptions.push(
		vscode.commands.registerCommand('pinjected-runner.run', (lineNumber: number) => {
			console.log("Running variable at line:", lineNumber);
			const editor = vscode.window.activeTextEditor;
			if (editor) {
				const document = editor.document;
				const varLine = document.lineAt(lineNumber - 1);
				const varText = varLine.text.trim();

				if (varText.includes(':IProxy')) {
					const varName = varText.split(':')[0].trim();
					runVariable(varName);
				}
			}
		})
	);

	context.subscriptions.push(
		vscode.languages.registerCodeLensProvider(
			{ language: 'python' },
			{
				provideCodeLenses: (document, token) => {
					const codeLenses: vscode.CodeLens[] = [];

					for (let i = 0; i < document.lineCount; i++) {
						const line = document.lineAt(i);
						if (line.text.trim().includes(':IProxy')) {
							const varName = line.text.trim().split(':')[0].trim();
							const codeLens = new vscode.CodeLens(line.range, {
								title: 'Run',
								command: 'pinjected-runner.run',
								arguments: [i + 1],
							});
							codeLenses.push(codeLens);
						}
					}

					return codeLenses;
				},
			}
		)
	);
}
// This method is called when your extension is deactivated
export function deactivate() { }
