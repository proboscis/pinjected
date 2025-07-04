// The module 'vscode' contains the VS Code extensibility API
// Import the module and reference it with the alias vscode in your code below
import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import * as cp from 'child_process';
import { promisify } from 'util';

const runConfigCache: { [filename: string]: { [varname: string]: RunConfig[] } } = {};
const execPromise = promisify(cp.exec);

interface CooldownInfo {
    lastUpdate: number;
    promise?: Promise<{[varName: string]: RunConfig[]}>;
}

const lastUpdateTime: { [filePath: string]: number } = {};
const COOLDOWN_PERIOD = 5000; // 5 seconds in milliseconds


async function execAsync(command: string): Promise<string> {
	console.log("Executing command:", command);
    try {
        const { stdout, stderr } = await execPromise(command, { encoding: 'utf8'});
        if (stderr) {
            console.warn('Command produced stderr output:', stderr);
        }
        return stdout;
    } catch (error) {
        if (error instanceof Error) {
            const execError = error as cp.ExecException;
            // console.error('Command execution failed:', execError.message);
            // if (execError.stderr) {
            //     console.error('Command execution failed:', execError.stderr.toString());
            // }
            throw execError;
        }
        throw error;
    }
}



class RunButtonDecoration extends vscode.Disposable {
	private readonly decorationType: vscode.TextEditorDecorationType;
	private isUpdating: boolean = false;

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
		if (this.isUpdating) {
			console.log('Update in progress. Ignoring new update request.');
			// vscode.window.showInformationMessage('Decoration update in progress. Please wait.');
			return;
		}

		this.updateDecorationsAsync(editor);
	}

	private async updateDecorationsAsync(editor: vscode.TextEditor): Promise<void> {
		this.isUpdating = true;
		console.log('RunButtonDecoration updateDecorationsAsync start');
		const decorations: vscode.DecorationOptions[] = [];

		try {
			// Perform the time-consuming task
			console.log('Updating decorations for:', editor.document.uri.fsPath);
			for (let i = 0; i < editor.document.lineCount; i++) {
				const line = editor.document.lineAt(i);
				if (isPinjectedVariable(line.text)) {
					console.log('pushing decoration to:', line.range);
					const varName = line.text.trim().split(':')[0].trim();
					//const configs:{[varName:string]:RunConfig[]} = await getRunConfigsInFile(editor.document.uri.fsPath);
					const configs = await getRunConfigs(editor.document.uri.fsPath, varName);
					var md = "";
					// to debug the hover message with command works, let's try the simplest command in vscode
					// md += `[Run this variable](command:workbench.action.files.newUntitledFile)`; -> This works fine.

					for (const runConfig of configs) {
						const encodedConfig = encodeURIComponent(JSON.stringify(runConfig));
						md += "[" + runConfig.name + `](command:pinjected-runner.runConfig?${encodedConfig})\n\n`;
						// clicking this does not work. It does not run the command. but why?
						// It is 
					}
					const mds = new vscode.MarkdownString(md);
					mds.isTrusted = true;

					decorations.push({
						range: line.range,
						hoverMessage: mds
						//hoverMessage: new vscode.MarkdownString(`[Run this variable](command:pinjected-runner.runFromHover?${encodeURIComponent(JSON.stringify([i + 1]))})`),
					});
				}

			}
			editor.setDecorations(this.decorationType, decorations);
		} catch (error) {
			console.error('Error in updateDecorationsAsync:', error);
			vscode.window.showErrorMessage('An error occurred while updating decorations.');
		} finally {
			this.isUpdating = false;
			console.log('RunButtonDecoration updateDecorationsAsync end');
		}
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

async function getPythonPath(): Promise<string> {
	const pythonExtension = vscode.extensions.getExtension('ms-python.python');
	if (pythonExtension) {
		const pythonApi = await pythonExtension.activate();
		return pythonApi.settings.getExecutionDetails().execCommand;
	}
	throw new Error('Python extension not found');
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
	const pinjectedPath = (await execAsync(`${python_path} -c "import pinjected; print(pinjected.__file__)"`)).trim();
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
		program: runConfig.script_path,//(await getPinjectedPath()) + "__main__.py",
		args:runConfig.arguments,
		env: {},
	};

	let launchConfigurations: any[] = [];
	if (fs.existsSync(launchJsonPath)) {
		const launchJsonContent = fs.readFileSync(launchJsonPath, 'utf8');
		try {
			const launchJson = JSON.parse(launchJsonContent);
			launchConfigurations = launchJson.configurations || [];
		} catch (error) {
			vscode.window.showErrorMessage(`Failed to parse launch.json. Error: ${error}`);
			throw error;
		}
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
	if (editor) {
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

// async function updateRunConfigsInFile(filePath: string) {
// 	// this gets called for every change in the file.
// 	// I need to add some cooltime to this function.



// 	const python_path = await getPythonPath();
// 	const cacheKey = `${filePath}`;
// 	try {
// 		const result = await execAsync(`${python_path} -m pinjected.meta_main pinjected.ide_supports.create_configs.create_idea_configurations "${filePath}"`);

// 		const pinjectedOutput: PinjectedOutput = extractPinjectedJson(result);

// 		runConfigCache[cacheKey] = pinjectedOutput.configs;
// 	} catch (error) {
// 		vscode.window.showErrorMessage(`Failed to get run configuration for file ${filePath}. Error: ${error}`);
// 		// Since the error is very long,
// 		// i need to show the full error message to the user. via vscode.
// 		// what options do i have?
// 		// 1. showErrorMessage
// 		// 2. showInformationMessage
// 		// 3. showWarningMessage


// 	}
// 	return runConfigCache[cacheKey];
// }

async function updateRunConfigsInFile(filePath: string) {
    const now = Date.now();
    const lastUpdate = lastUpdateTime[filePath] || 0;
    
    // Check if we're still in cooldown period
    if (now - lastUpdate < COOLDOWN_PERIOD) {
        console.log('Skipping update due to cooldown period');
        return runConfigCache[filePath];
    }

    const python_path = await getPythonPath();
    try {
        const result = await execAsync(`${python_path} -m pinjected.meta_main pinjected.ide_supports.create_configs.create_idea_configurations "${filePath}"`);
        
        const pinjectedOutput: PinjectedOutput = extractPinjectedJson(result);
        runConfigCache[filePath] = pinjectedOutput.configs;
        
        // Update the last update time
        lastUpdateTime[filePath] = now;
    } catch (error) {
        vscode.window.showErrorMessage(`Failed to get run configuration for file ${filePath}. Error: ${error}`);
    }
    
    return runConfigCache[filePath];
}

async function getRunConfigs(filePath: string, varName: string): Promise<RunConfig[]> {
	const python_path = await getPythonPath();
	const cacheKey = `${filePath}`;
	if (cacheKey in runConfigCache && varName in runConfigCache[cacheKey]) {
		return runConfigCache[cacheKey][varName];
	} else {
		await updateRunConfigsInFile(filePath);
		return runConfigCache[cacheKey][varName];
	}
}

async function visualizePinjectedVariable(filePath: string, varName: string) {
	const python_path = await getPythonPath();
	const pinjected_path = await getPinjectedPath();
	const viz_script_path = path.join(pinjected_path, "run_config_utils.py");
	// hmm, you need a default design path. 
	// const visConfig:RunConfig = {
	// 	name: "Visualize "+varName,
	// 	script_path: viz_script_path,
	// 	interpreter_path: python_path,
	// 	arguments: ["run_injected","visualize",varName,design_path],	
	// 	working_dir: ""
	// };

}

function isPinjectedVariable(line: string): boolean {
	line = line.trim();
	line = line.replace(" ", "");
	return line.includes(':IProxy') || line.includes(":Injected") || line.includes(":DelegatedVar");
}

export function activate(context: vscode.ExtensionContext) {
	runButtonDecoration = new RunButtonDecoration();

	
	// vscode.window.onDidChangeActiveTextEditor(
	// 	(editor) => {
	// 		if (editor) {
	// 			runButtonDecoration.updateDecorations(editor);
	// 		}
	// 	},
	// 	null,
	// 	context.subscriptions
	// );

	// vscode.workspace.onDidChangeTextDocument(
	// 	(event) => {
	// 		if (vscode.window.activeTextEditor && event.document === vscode.window.activeTextEditor.document) {
	// 			runButtonDecoration.updateDecorations(vscode.window.activeTextEditor);
	// 		}
	// 	},
	// 	null,
	// 	context.subscriptions
	// );


	context.subscriptions.push(
		vscode.commands.registerCommand('pinjected-runner.run', (lineNumber: number) => {
			console.log("Running variable at line:", lineNumber);
			const editor = vscode.window.activeTextEditor;
			if (editor) {
				const document = editor.document;
				const varLine = document.lineAt(lineNumber - 1);
				const varText = varLine.text.trim();
				if (isPinjectedVariable(varText)) {
					const varName = varText.split(':')[0].trim();
					runVariable(varName);
				}
			}
		})
	);
	context.subscriptions.push(
		vscode.commands.registerCommand('pinjected-runner.visualize', (fileName:string,varName:string) => {
			console.log('Visualizing variable:',varName);
			/**
			 * 1. run pinjected to get the generated graph html file path
			 * 2. open the file in vscode
			 */
			visualizePinjectedVariable(fileName,varName);
		})
	);
	context.subscriptions.push(
		vscode.commands.registerCommand('pinjected-runner.runConfig', (runConfig: RunConfig) => {

			vscode.window.showInformationMessage(`Running configuration: ${runConfig.name}`);
			const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
			if (workspaceFolder) {
				registerDebugConfiguration(runConfig, runConfig.name);
				vscode.debug.startDebugging(workspaceFolder, `Debug ${runConfig.name}`);
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
						if (isPinjectedVariable(line.text)) {
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
