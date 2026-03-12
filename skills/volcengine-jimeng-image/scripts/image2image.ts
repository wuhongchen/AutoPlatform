#!/usr/bin/env ts-node
/**
 * 图生图脚本 - Image to Image
 * 基于参考图生成新图片
 *
 * 用法：ts-node image2image.ts "提示词" <参考图路径> [选项]
 */

import * as path from 'path';
import * as fs from 'fs';
import * as crypto from 'crypto';
import {
  REQ_KEYS,
  VALID_RATIOS,
  submitTask,
  waitForTask,
  getCredentials,
  outputError
} from './common';

interface Image2ImageOptions {
  prompt: string;
  imagePath: string;
  version: 'v30' | 'v31';
  ratio: string;
  count: number;
  strength: number; // 重绘强度 0-1
  seed?: number;
  outputDir: string;
  download: boolean;
  debug: boolean;
}

function parseArgs(): Image2ImageOptions {
  const args = process.argv.slice(2);

  if (args.length < 2) {
    console.error('用法：ts-node image2image.ts "提示词" <参考图路径> [选项]');
    console.error('');
    console.error('选项:');
    console.error('  --version <v30|v31>      API 版本 (默认：v31)');
    console.error('  --ratio <宽高比>         图片宽高比 (默认：1:1)');
    console.error('  --count <数量>           生成数量 1-4 (默认：1)');
    console.error('  --strength <强度>        重绘强度 0-1 (默认：0.7)');
    console.error('  --seed <种子>            随机种子 (可选)');
    console.error('  --output <目录>          图片下载目录 (默认：./output)');
    console.error('  --no-download            不下载图片，只返回 URL');
    console.error('  --debug                  开启调试模式');
    process.exit(1);
  }

  const prompt = args[0];
  const imagePath = args[1];
  let version: 'v30' | 'v31' = 'v31';
  let ratio = '1:1';
  let count = 1;
  let strength = 0.7;
  let seed: number | undefined;
  let outputDir = './output';
  let download = true;
  let debug = false;

  for (let i = 2; i < args.length; i++) {
    switch (args[i]) {
      case '--version':
        const v = args[++i];
        if (v !== 'v30' && v !== 'v31') {
          throw new Error(`不支持的版本：${v}，支持的值：v30, v31`);
        }
        version = v;
        break;
      case '--ratio':
        ratio = args[++i];
        if (!VALID_RATIOS.includes(ratio)) {
          throw new Error(`不支持的宽高比：${ratio}，支持的值：${VALID_RATIOS.join(', ')}`);
        }
        break;
      case '--count':
        count = parseInt(args[++i]);
        if (count < 1 || count > 4) {
          throw new Error('生成数量必须在 1-4 之间');
        }
        break;
      case '--strength':
        strength = parseFloat(args[++i]);
        if (strength < 0 || strength > 1) {
          throw new Error('重绘强度必须在 0-1 之间');
        }
        break;
      case '--seed':
        seed = parseInt(args[++i]);
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

  // 验证图片路径
  if (!fs.existsSync(imagePath)) {
    throw new Error(`参考图不存在：${imagePath}`);
  }

  return {
    prompt,
    imagePath,
    version,
    ratio,
    count,
    strength,
    seed,
    outputDir,
    download,
    debug
  };
}

async function main() {
  try {
    const options = parseArgs();
    const { accessKey, secretKey } = getCredentials();

    console.log(`\n🎨 图生图任务`);
    console.log(`提示词：${options.prompt}`);
    console.log(`参考图：${options.imagePath}`);
    console.log(`版本：${options.version}`);
    console.log(`重绘强度：${options.strength}`);
    console.log(`数量：${options.count}`);
    console.log(`宽高比：${options.ratio}`);
    console.log('');

    // 读取参考图并转换为 Base64
    const imageBuffer = fs.readFileSync(options.imagePath);
    const imageBase64 = imageBuffer.toString('base64');

    // 构建请求体
    const body: Record<string, any> = {
      req_key: REQ_KEYS.I2I_V30,
      prompt: options.prompt,
      image_base64: imageBase64,
      strength: options.strength,
      count: options.count
    };

    // 添加宽高比
    const [width, height] = options.ratio.split(':').map(Number);
    if (options.ratio === '1:1') {
      body.width = 1024;
      body.height = 1024;
    } else if (options.ratio === '16:9') {
      body.width = 1024;
      body.height = 576;
    } else if (options.ratio === '9:16') {
      body.width = 576;
      body.height = 1024;
    } else {
      body.width = width * 256;
      body.height = height * 256;
    }

    // 添加种子
    if (options.seed) {
      body.seed = options.seed;
    }

    // 提交任务
    console.log('提交任务...');
    const { taskId } = await submitTask(
      accessKey,
      secretKey,
      REQ_KEYS.I2I_V30,
      body
    );

    console.log(`任务已提交，TaskId: ${taskId}`);

    // 等待任务完成
    console.log('正在等待任务完成...');
    const result = await waitForTask(accessKey, secretKey, REQ_KEYS.I2I_V30, taskId);

    if (!result.images || result.images.length === 0) {
      throw new Error('任务完成但未生成图片');
    }

    // 保存结果
    const hash = crypto.createHash('md5').update(options.prompt).digest('hex');
    const outputDir = path.resolve(options.outputDir, hash);
    
    if (!fs.existsSync(outputDir)) {
      fs.mkdirSync(outputDir, { recursive: true });
    }

    // 保存参数
    const paramPath = path.join(outputDir, 'param.json');
    fs.writeFileSync(paramPath, JSON.stringify({
      prompt: options.prompt,
      imagePath: options.imagePath,
      version: options.version,
      ratio: options.ratio,
      count: options.count,
      strength: options.strength,
      seed: options.seed,
      req_key: REQ_KEYS.I2I_V30,
      timestamp: new Date().toISOString()
    }, null, 2));

    // 保存任务 ID
    const taskIdPath = path.join(outputDir, 'taskId.txt');
    fs.writeFileSync(taskIdPath, taskId);

    // 保存图片
    console.log(`任务完成，正在保存 ${result.images.length} 张图片...`);
    const imagePaths: string[] = [];
    
    for (let i = 0; i < result.images.length; i++) {
      const imageUrl = result.images[i].url;
      const imagePath = path.join(outputDir, `${i + 1}.jpg`);
      
      if (options.download) {
        const imageResp = await fetch(imageUrl);
        const arrayBuffer = await imageResp.arrayBuffer();
        const buffer = Buffer.from(arrayBuffer);
        fs.writeFileSync(imagePath, buffer);
        imagePaths.push(imagePath);
        console.log(`  - ${imagePath}`);
      } else {
        console.log(`  - ${imageUrl}`);
      }
    }

    // 输出结果
    console.log('');
    console.log(JSON.stringify({
      success: true,
      prompt: options.prompt,
      imagePath: options.imagePath,
      version: options.version,
      ratio: options.ratio,
      count: options.count,
      strength: options.strength,
      taskId,
      images: options.download ? imagePaths : result.images.map(img => img.url),
      outputDir
    }, null, 2));

  } catch (error: any) {
    console.error('');
    outputError(error);
    process.exit(1);
  }
}

main();
