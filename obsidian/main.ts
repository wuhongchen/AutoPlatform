import { App, Modal, Notice, Plugin, PluginSettingTab, Setting } from "obsidian";
import { spawn } from "child_process";
import * as fs from "fs";
import * as path from "path";

interface AutoInfoPluginSettings {
  backendRoot: string;
  pythonPath: string;
  defaultRole: string;
  defaultModel: string;
  nonInteractive: boolean;
  autoInstall: boolean;
  pipelineBatchSize: number;
  scheduleMinutes: number;
}

const DEFAULT_SETTINGS: AutoInfoPluginSettings = {
  backendRoot: "",
  pythonPath: "python3",
  defaultRole: "tech_expert",
  defaultModel: "auto",
  nonInteractive: true,
  autoInstall: false,
  pipelineBatchSize: 3,
  scheduleMinutes: 30,
};

class UrlInputModal extends Modal {
  private onSubmit: (url: string) => void;
  private titleText: string;

  constructor(app: App, titleText: string, onSubmit: (url: string) => void) {
    super(app);
    this.onSubmit = onSubmit;
    this.titleText = titleText;
  }

  onOpen() {
    const { contentEl } = this;
    contentEl.empty();
    contentEl.createEl("h3", { text: this.titleText });
    const input = contentEl.createEl("input", {
      type: "text",
      placeholder: "https://mp.weixin.qq.com/s/xxxx",
    });
    input.style.width = "100%";
    input.style.marginBottom = "12px";

    const runBtn = contentEl.createEl("button", { text: "运行" });
    runBtn.onclick = () => {
      const url = input.value.trim();
      if (!url) {
        new Notice("请输入 URL");
        return;
      }
      this.close();
      this.onSubmit(url);
    };
  }

  onClose() {
    this.contentEl.empty();
  }
}

export default class AutoInfoObsidianPlugin extends Plugin {
  settings: AutoInfoPluginSettings;
  private scheduleTimer: number | null = null;
  private running = false;

  async onload() {
    await this.loadSettings();
    this.addSettingTab(new AutoInfoSettingTab(this.app, this));

    this.addCommand({
      id: "autoinfo-scan-inspiration",
      name: "AutoInfo: 灵感库扫描与评估",
      callback: async () => this.runInspirationScan(),
    });

    this.addCommand({
      id: "autoinfo-pipeline-once",
      name: "AutoInfo: 内容流水线改写与发布（单次）",
      callback: async () => this.runPipelineOnce(),
    });

    this.addCommand({
      id: "autoinfo-single-article",
      name: "AutoInfo: 单篇文章即时处理",
      callback: () =>
        new UrlInputModal(this.app, "输入单篇文章 URL", async (url) => {
          await this.runSingleArticle(url);
        }).open(),
    });

    this.addCommand({
      id: "autoinfo-demo-full-flow",
      name: "AutoInfo: 全流程 Demo（默认 skip publish）",
      callback: () =>
        new UrlInputModal(this.app, "输入全流程 Demo URL", async (url) => {
          await this.runFullDemo(url, true);
        }).open(),
    });

    this.addCommand({
      id: "autoinfo-start-scheduled-pipeline",
      name: "AutoInfo: 启动全流程定时执行（pipeline-once）",
      callback: () => this.startScheduledPipeline(),
    });

    this.addCommand({
      id: "autoinfo-stop-scheduled-pipeline",
      name: "AutoInfo: 停止全流程定时执行",
      callback: () => this.stopScheduledPipeline(),
    });

    this.addCommand({
      id: "autoinfo-check-env",
      name: "AutoInfo: 环境体检",
      callback: async () => this.checkEnv(),
    });

    this.addRibbonIcon("rocket", "AutoInfo: 流水线单次巡检", async () => {
      await this.runPipelineOnce();
    });
  }

  onunload() {
    this.stopScheduledPipeline(false);
  }

  async loadSettings() {
    this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
  }

  async saveSettings() {
    await this.saveData(this.settings);
  }

  private ensureBackendRoot(): boolean {
    const root = this.settings.backendRoot.trim();
    if (!root) {
      new Notice("请先在插件设置里填写 backendRoot");
      return false;
    }
    if (!fs.existsSync(root)) {
      new Notice("backendRoot 不存在，请检查路径");
      return false;
    }
    return true;
  }

  private getRunEnv(): NodeJS.ProcessEnv {
    return {
      ...process.env,
      OPENCLAW_NON_INTERACTIVE: this.settings.nonInteractive ? "1" : "0",
      OPENCLAW_AUTO_INSTALL: this.settings.autoInstall ? "1" : "0",
      OPENCLAW_PIPELINE_BATCH_SIZE: String(this.settings.pipelineBatchSize || 3),
    };
  }

  private async exec(
    cmd: string,
    args: string[],
    label: string,
    cwd?: string,
    env?: NodeJS.ProcessEnv
  ): Promise<number> {
    return await new Promise((resolve) => {
      const workdir = cwd || this.settings.backendRoot;
      const child = spawn(cmd, args, {
        cwd: workdir,
        env: env || this.getRunEnv(),
        shell: false,
      });

      let stderr = "";
      child.stdout.on("data", (chunk) => {
        console.log(`[${label}]`, chunk.toString());
      });
      child.stderr.on("data", (chunk) => {
        const text = chunk.toString();
        stderr += text;
        console.error(`[${label}][ERR]`, text);
      });
      child.on("close", (code) => {
        if (code === 0) {
          new Notice(`${label} 执行完成`);
        } else {
          const hint = stderr.slice(0, 140).replace(/\s+/g, " ").trim();
          new Notice(`${label} 执行失败 (code=${code}) ${hint ? `: ${hint}` : ""}`);
        }
        resolve(code ?? 1);
      });
    });
  }

  private async runInspirationScan() {
    if (!this.ensureBackendRoot()) return;
    await this.exec(this.settings.pythonPath, ["core/manager_inspiration.py"], "灵感库扫描");
  }

  private async runPipelineOnce(fromSchedule = false) {
    if (!this.ensureBackendRoot()) return;
    if (this.running) {
      if (!fromSchedule) new Notice("当前已有任务执行中，请稍后");
      return;
    }
    this.running = true;
    try {
      const runSh = path.join(this.settings.backendRoot, "run.sh");
      await this.exec(runSh, ["pipeline-once"], "流水线单次巡检");
    } finally {
      this.running = false;
    }
  }

  private async runSingleArticle(url: string) {
    if (!this.ensureBackendRoot()) return;
    const runSh = path.join(this.settings.backendRoot, "run.sh");
    await this.exec(runSh, [url, this.settings.defaultRole, this.settings.defaultModel], "单篇即时处理");
  }

  private async runFullDemo(url: string, skipPublish: boolean) {
    if (!this.ensureBackendRoot()) return;
    const args = ["scripts/internal/demo_full_flow.py", "--url", url];
    if (skipPublish) args.push("--skip-publish");
    await this.exec(this.settings.pythonPath, args, skipPublish ? "全流程Demo(联调)" : "全流程Demo(发布)");
  }

  private startScheduledPipeline() {
    if (!this.ensureBackendRoot()) return;
    if (this.scheduleTimer) {
      new Notice("定时任务已在运行");
      return;
    }
    const ms = Math.max(1, this.settings.scheduleMinutes) * 60 * 1000;
    this.scheduleTimer = window.setInterval(async () => {
      await this.runPipelineOnce(true);
    }, ms);
    new Notice(`已启动定时巡检：每 ${this.settings.scheduleMinutes} 分钟执行一次 pipeline-once`);
  }

  private stopScheduledPipeline(notice = true) {
    if (this.scheduleTimer) {
      window.clearInterval(this.scheduleTimer);
      this.scheduleTimer = null;
      if (notice) new Notice("已停止定时巡检");
      return;
    }
    if (notice) new Notice("当前没有运行中的定时巡检");
  }

  private async checkEnv() {
    if (!this.ensureBackendRoot()) return;
    await this.exec(this.settings.pythonPath, ["scripts/internal/check_env.py"], "环境体检");
  }
}

class AutoInfoSettingTab extends PluginSettingTab {
  plugin: AutoInfoObsidianPlugin;

  constructor(app: App, plugin: AutoInfoObsidianPlugin) {
    super(app, plugin);
    this.plugin = plugin;
  }

  display(): void {
    const { containerEl } = this;
    containerEl.empty();

    containerEl.createEl("h2", { text: "AutoInfo Obsidian 入口设置" });

    new Setting(containerEl)
      .setName("后端根目录")
      .setDesc("autoinfo-platform 绝对路径，例如 /Users/xxx/autoinfo-platform")
      .addText((text) =>
        text
          .setPlaceholder("/absolute/path/to/autoinfo-platform")
          .setValue(this.plugin.settings.backendRoot)
          .onChange(async (value) => {
            this.plugin.settings.backendRoot = value.trim();
            await this.plugin.saveSettings();
          })
      );

    new Setting(containerEl)
      .setName("Python 命令")
      .setDesc("默认 python3")
      .addText((text) =>
        text
          .setPlaceholder("python3")
          .setValue(this.plugin.settings.pythonPath)
          .onChange(async (value) => {
            this.plugin.settings.pythonPath = value.trim() || "python3";
            await this.plugin.saveSettings();
          })
      );

    new Setting(containerEl)
      .setName("默认角色")
      .setDesc("单篇处理时传入 run.sh 的角色参数")
      .addText((text) =>
        text.setValue(this.plugin.settings.defaultRole).onChange(async (value) => {
          this.plugin.settings.defaultRole = value.trim() || "tech_expert";
          await this.plugin.saveSettings();
        })
      );

    new Setting(containerEl)
      .setName("默认模型")
      .setDesc("单篇处理默认模型 key，例如 auto / kimi-k2.5")
      .addText((text) =>
        text.setValue(this.plugin.settings.defaultModel).onChange(async (value) => {
          this.plugin.settings.defaultModel = value.trim() || "auto";
          await this.plugin.saveSettings();
        })
      );

    new Setting(containerEl)
      .setName("非交互模式")
      .setDesc("推荐开启，避免命令等待输入")
      .addToggle((toggle) =>
        toggle.setValue(this.plugin.settings.nonInteractive).onChange(async (value) => {
          this.plugin.settings.nonInteractive = value;
          await this.plugin.saveSettings();
        })
      );

    new Setting(containerEl)
      .setName("自动安装依赖")
      .setDesc("默认关闭（更快）")
      .addToggle((toggle) =>
        toggle.setValue(this.plugin.settings.autoInstall).onChange(async (value) => {
          this.plugin.settings.autoInstall = value;
          await this.plugin.saveSettings();
        })
      );

    new Setting(containerEl)
      .setName("pipeline 批大小")
      .setDesc("对应 OPENCLAW_PIPELINE_BATCH_SIZE")
      .addSlider((slider) =>
        slider
          .setLimits(1, 10, 1)
          .setValue(this.plugin.settings.pipelineBatchSize)
          .setDynamicTooltip()
          .onChange(async (value) => {
            this.plugin.settings.pipelineBatchSize = value;
            await this.plugin.saveSettings();
          })
      );

    new Setting(containerEl)
      .setName("定时巡检间隔（分钟）")
      .setDesc("用于全流程定时执行")
      .addText((text) =>
        text.setValue(String(this.plugin.settings.scheduleMinutes)).onChange(async (value) => {
          const num = Number(value);
          this.plugin.settings.scheduleMinutes = Number.isFinite(num) && num > 0 ? Math.floor(num) : 30;
          await this.plugin.saveSettings();
        })
      );
  }
}

