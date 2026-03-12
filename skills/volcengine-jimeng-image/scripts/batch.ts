#!/usr/bin/env ts-node
/**
 * 批量任务管理脚本
 * 批量提交和管理多个生成任务
 *
 * 用法：ts-node batch.ts <任务文件> [选项]
 */

import * as path from 'path';
import * as fs from 'fs';
import * as crypto from 'crypto';
import {
  submitTask,
  waitForTask,
  getCredentials,
  outputError
} from './common';

interface BatchTask {
  prompt: string;
  version?: string;
  ratio?: string;
  count?: number;
}

interface BatchOptions {
  taskFile: string;
  maxConcurrent: number;
  outputDir: string;
  download: boolean;
  debug: boolean;
}

function parseArgs(): BatchOptions {
  const args = process.argv.slice(2);

  if (args.length < 1) {
    console.error('用法：ts-node batch.ts <任务文件> [选项]');
    console.error('');
    console.error('任务文件格式 (JSON):');
    console.error('[');
    console.error('  {');
    console.error('    "prompt": "提示词 1",');
    console.error('    "version": "v40",');
    console.error('    "ratio": "16:9",');
    console.error('    "count": 1');
    console.error('  },');
    console.error('  ...');
    console.error(']');
    console.error('');
    console.error('选项:');
    console.error('  --max-concurrent <数量>   最大并发数 (默认：3)');
    console.error('  --output <目录>          图片下载目录 (默认：./output)');
    console.error('  --no-download            不下载图片，只返回 URL');
    console.error('  --debug                  开启调试模式');
    process.exit(1);
  }

  const taskFile = args[0];
  let maxConcurrent = 3;
  let outputDir = './output';
  let download = true;
  let debug = false;

  for (let i = 1; i < args.length; i++) {
    switch (args[i]) {
      case '--max-concurrent':
        maxConcurrent = parseInt(args[++i]);
        break;
      case '--output':
        outputDir = args[++i];
        break;
      case '--no-download':
        download = false;
        break;
      case '--debug':
        debug = true;
        process.env.DEBUG = 'true';
        break;
    }
  }

  // 验证任务文件
  if (!fs.existsSync(taskFile)) {
    throw new Error(`任务文件不存在：${taskFile}`);
  }

  return {
    taskFile,
    maxConcurrent,
    outputDir,
    download,
    debug
  };
}

async function processTask(
  task: BatchTask,
  index: number,
  accessKey: string,
  secretKey: string,
  outputDir: string,
  download: boolean
) {
  console.log(`\n[${index}] 处理任务：${task.prompt}`);

  try {
    // 构建请求体
    const body: Record<string, any> = {
      req_key: `jimeng_t2i_${task.version || 'v31'}`,
      prompt: task.prompt,
      count: task.count || 1
    };

    // 添加宽高比
    if (task.ratio) {
      const [width, height] = task.ratio.split(':').map(Number);
      if (task.ratio === '1:1') {
        body.width = 1024;
        body.height = 1024;
      } else if (task.ratio === '16:9') {
        body.width = 1024;
        body.height = 576;
      } else if (task.ratio === '9:16') {
        body.width = 576;
        body.height = 1024;
      } else {
        body.width = width * 256;
        body.height = height * 256;
      }
    }

    // 提交任务
    console.log(`  提交任务...`);
    const { taskId } = await submitTask(
      accessKey,
      secretKey,
      body.req_key,
      body
    );

    console.log(`  任务已提交，TaskId: ${taskId}`);

    // 等待任务完成
    console.log(`  等待任务完成...`);
    const result = await waitForTask(
      accessKey,
      secretKey,
      body.req_key,
      taskId
    );

    if (!result.images || result.images.length === 0) {
      throw new Error('任务完成但未生成图片');
    }

    // 保存结果
    const hash = crypto.createHash('md5').update(task.prompt).digest('hex');
    const taskOutputDir = path.join(outputDir, `batch_${index}_${hash}`);
    
    if (!fs.existsSync(taskOutputDir)) {
      fs.mkdirSync(taskOutputDir, { recursive: true });
    }

    // 保存参数
    const paramPath = path.join(taskOutputDir, 'param.json');
    fs.writeFileSync(paramPath, JSON.stringify({
      ...task,
      taskId,
      timestamp: new Date().toISOString()
    }, null, 2));

    // 保存任务 ID
    const taskIdPath = path.join(taskOutputDir, 'taskId.txt');
    fs.writeFileSync(taskIdPath, taskId);

    // 保存图片
    console.log(`  保存 ${result.images.length} 张图片...`);
    const imagePaths: string[] = [];
    
    for (let i = 0; i < result.images.length; i++) {
      const imageUrl = result.images[i].url;
      const imagePath = path.join(taskOutputDir, `${i + 1}.jpg`);
      
      if (download) {
        const imageResp = await fetch(imageUrl);
        const arrayBuffer = await imageResp.arrayBuffer();
        const buffer = Buffer.from(arrayBuffer);
        fs.writeFileSync(imagePath, buffer);
        imagePaths.push(imagePath);
      }
    }

    console.log(`  任务 ${index} 完成`);

    return {
      success: true,
      index,
      prompt: task.prompt,
      taskId,
      images: download ? imagePaths : result.images.map(img => img.url)
    };

  } catch (error: any) {
    console.error(`  任务 ${index} 失败：${error.message}`);
    return {
      success: false,
      index,
      prompt: task.prompt,
      error: error.message
    };
  }
}

async function main() {
  try {
    const options = parseArgs();
    const { accessKey, secretKey } = getCredentials();

    // 读取任务文件
    const taskContent = fs.readFileSync(options.taskFile, 'utf-8');
    const tasks: BatchTask[] = JSON.parse(taskContent);

    console.log(`\n📦 批量任务管理`);
    console.log(`任务文件：${options.taskFile}`);
    console.log(`任务数量：${tasks.length}`);
    console.log(`最大并发：${options.maxConcurrent}`);
    console.log(`输出目录：${options.outputDir}`);
    console.log('');

    // 创建输出目录
    if (!fs.existsSync(options.outputDir)) {
      fs.mkdirSync(options.outputDir, { recursive: true });
    }

    // 批量处理任务
    const results: any[] = [];
    const queue = [...tasks];
    const running = new Set<Promise<any>>();

    console.log('开始处理任务...\n');

    while (queue.length > 0 || running.size > 0) {
      // 启动新任务直到达到并发限制
      while (running.size < options.maxConcurrent && queue.length > 0) {
        const task = queue.shift()!;
        const index = tasks.indexOf(task) + 1;
        const promise = processTask(
          task,
          index,
          accessKey,
          secretKey,
          options.outputDir,
          options.download
        );
        running.add(promise);
      }

      // 等待一个任务完成
      if (running.size > 0) {
        const done = await Promise.race(running);
        results.push(done);
        running.delete(done);
      }
    }

    // 输出结果
    console.log('\n\n=== 批量任务完成 ===\n');
    
    const successCount = results.filter(r => r.success).length;
    const failCount = results.filter(r => !r.success).length;

    console.log(`总任务数：${tasks.length}`);
    console.log(`成功：${successCount}`);
    console.log(`失败：${failCount}`);
    console.log('');

    console.log('结果详情:');
    for (const result of results) {
      if (result.success) {
        console.log(`  ✅ [${result.index}] ${result.prompt}`);
      } else {
        console.log(`  ❌ [${result.index}] ${result.prompt} - ${result.error}`);
      }
    }

    // 保存汇总结果
    const summaryPath = path.join(options.outputDir, 'batch-summary.json');
    fs.writeFileSync(summaryPath, JSON.stringify({
      total: tasks.length,
      success: successCount,
      fail: failCount,
      results,
      timestamp: new Date().toISOString()
    }, null, 2));

    console.log(`\n汇总结果已保存到：${summaryPath}`);

  } catch (error: any) {
    console.error('');
    outputError(error);
    process.exit(1);
  }
}

main();
