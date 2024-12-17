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
const fs = __importStar(require("fs"));
const cp = __importStar(require("child_process"));
const util_1 = require("util");
const runConfigCache = {};
const execPromise = (0, util_1.promisify)(cp.exec);
const lastUpdateTime = {};
const COOLDOWN_PERIOD = 5000; // 5 seconds in milliseconds
async function execAsync(command) {
    console.log("Executing command:", command);
    try {
        const { stdout, stderr } = await execPromise(command, { encoding: 'utf8' });
        if (stderr) {
            console.warn('Command produced stderr output:', stderr);
        }
        return stdout;
    }
    catch (error) {
        if (error instanceof Error) {
            const execError = error;
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
    decorationType;
    isUpdating = false;
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
        if (this.isUpdating) {
            console.log('Update in progress. Ignoring new update request.');
            // vscode.window.showInformationMessage('Decoration update in progress. Please wait.');
            return;
        }
        this.updateDecorationsAsync(editor);
    }
    async updateDecorationsAsync(editor) {
        this.isUpdating = true;
        console.log('RunButtonDecoration updateDecorationsAsync start');
        const decorations = [];
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
        }
        catch (error) {
            console.error('Error in updateDecorationsAsync:', error);
            vscode.window.showErrorMessage('An error occurred while updating decorations.');
        }
        finally {
            this.isUpdating = false;
            console.log('RunButtonDecoration updateDecorationsAsync end');
        }
    }
}
let runButtonDecoration;
async function getPythonPath() {
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
async function getPinjectedPath() {
    const python_path = await getPythonPath();
    const pinjectedPath = (await execAsync(`${python_path} -c "import pinjected; print(pinjected.__file__)"`)).trim();
    const pinjectedPackagePath = pinjectedPath.replace("__init__.py", "");
    return pinjectedPackagePath;
}
async function registerDebugConfiguration(runConfig, varName) {
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
        program: runConfig.script_path, //(await getPinjectedPath()) + "__main__.py",
        args: runConfig.arguments,
        env: {},
    };
    let launchConfigurations = [];
    if (fs.existsSync(launchJsonPath)) {
        const launchJsonContent = fs.readFileSync(launchJsonPath, 'utf8');
        try {
            const launchJson = JSON.parse(launchJsonContent);
            launchConfigurations = launchJson.configurations || [];
        }
        catch (error) {
            vscode.window.showErrorMessage(`Failed to parse launch.json. Error: ${error}`);
            throw error;
        }
    }
    // replace a configuration with the same name
    const existingConfigIndex = launchConfigurations.findIndex((config) => config.name === launchConfig.name);
    if (existingConfigIndex !== -1) {
        launchConfigurations[existingConfigIndex] = launchConfig;
    }
    else {
        //add a new configuration if not found
        launchConfigurations.push(launchConfig);
    }
    const updatedLaunchJson = {
        version: '0.2.0',
        configurations: launchConfigurations,
    };
    fs.writeFileSync(launchJsonPath, JSON.stringify(updatedLaunchJson, null, 2), 'utf8');
}
async function runVariable(varName) {
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
            const runConfig = runConfigs[0];
            await registerDebugConfiguration(runConfig, varName);
            const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
            vscode.debug.startDebugging(workspaceFolder, `Debug ${varName}`);
        }
    }
}
function extractPinjectedJson(text) {
    const pinjectedRegex = /<pinjected>(.*?)<\/pinjected>/s;
    const match = text.match(pinjectedRegex);
    if (match && match[1]) {
        try {
            return JSON.parse(match[1]);
        }
        catch (error) {
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
async function updateRunConfigsInFile(filePath) {
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
        const pinjectedOutput = extractPinjectedJson(result);
        runConfigCache[filePath] = pinjectedOutput.configs;
        // Update the last update time
        lastUpdateTime[filePath] = now;
    }
    catch (error) {
        vscode.window.showErrorMessage(`Failed to get run configuration for file ${filePath}. Error: ${error}`);
    }
    return runConfigCache[filePath];
}
async function getRunConfigs(filePath, varName) {
    const python_path = await getPythonPath();
    const cacheKey = `${filePath}`;
    if (cacheKey in runConfigCache && varName in runConfigCache[cacheKey]) {
        return runConfigCache[cacheKey][varName];
    }
    else {
        await updateRunConfigsInFile(filePath);
        return runConfigCache[cacheKey][varName];
    }
}
async function visualizePinjectedVariable(filePath, varName) {
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
function isPinjectedVariable(line) {
    line = line.trim();
    line = line.replace(" ", "");
    return line.includes(':IProxy') || line.includes(":Injected") || line.includes(":DelegatedVar");
}
function activate(context) {
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
    context.subscriptions.push(vscode.commands.registerCommand('pinjected-runner.run', (lineNumber) => {
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
    }));
    context.subscriptions.push(vscode.commands.registerCommand('pinjected-runner.visualize', (fileName, varName) => {
        console.log('Visualizing variable:', varName);
        /**
         * 1. run pinjected to get the generated graph html file path
         * 2. open the file in vscode
         */
        visualizePinjectedVariable(fileName, varName);
    }));
    context.subscriptions.push(vscode.commands.registerCommand('pinjected-runner.runConfig', (runConfig) => {
        vscode.window.showInformationMessage(`Running configuration: ${runConfig.name}`);
        const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
        if (workspaceFolder) {
            registerDebugConfiguration(runConfig, runConfig.name);
            vscode.debug.startDebugging(workspaceFolder, `Debug ${runConfig.name}`);
        }
    }));
    context.subscriptions.push(vscode.languages.registerCodeLensProvider({ language: 'python' }, {
        provideCodeLenses: (document, token) => {
            const codeLenses = [];
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
    }));
}
// This method is called when your extension is deactivated
function deactivate() { }
//# sourceMappingURL=extension.js.map