#!/usr/bin/env ts-node
/**
 * 智能扩图脚本 - Outpainting
 * 智能扩展图片边界
 *
 * 用法：ts-node outpaint.ts <图片路径> [选项]
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

interface OutpaintOptions {
  imagePath: string;
  targetWidth: number;
  targetHeight: number;
  prompt?: string;
  outputDir: string;
  download: boolean;
  debug: boolean;
}

function parseArgs(): OutpaintOptions {
  const args = process.argv.slice(2);

  if (args.length < 1) {
    console.error('用法：ts-node outpaint.ts <图片路径> [选项]');
    console.error('');
    console.error('选项:');
    console.error('  --width <宽度>           目标宽度 (默认：原图宽度*1.5)');
    console.error('  --height <高度>          目标高度 (默认：原图高度*1.5)');
    console.error('  --prompt <提示词>        扩图提示词 (可选)');
    console.error('  --output <目录>          图片下载目录 (默认：./output)');
    console.error('  --no-download            不下载图片，只返回 URL');
    console.error('  --debug                  开启调试模式');
    process.exit(1);
  }

  const imagePath = args[0];
  let targetWidth: number | undefined;
  let targetHeight: number | undefined;
  let prompt: string | undefined;
  let outputDir = './output';
  let download = true;
  let debug = false;

  for (let i = 1; i < args.length; i++) {
    switch (args[i]) {
      case '--width':
        targetWidth = parseInt(args[++i]);
        break;
      case '--height':
        targetHeight = parseInt(args[++i]);
        break;
      case '--prompt':
        prompt = args[++i];
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
    throw new Error(`图片不存在：${imagePath}`);
  }

  return {
    imagePath,
    targetWidth: targetWidth!,
    targetHeight: targetHeight!,
    prompt,
    outputDir,
    download,
    debug
  };
}

async function main() {
  try {
    const options = parseArgs();
    const { accessKey, secretKey } = getCredentials();

    console.log(`\n🖼️ 智能扩图任务`);
    console.log(`原图：${options.imagePath}`);
    if (options.targetWidth && options.targetHeight) {
      console.log(`目标尺寸：${options.targetWidth}x${options.targetHeight}`);
    }
    if (options.prompt) {
      console.log(`提示词：${options.prompt}`);
    }
    console.log('');

    // 读取原图
    const imageBuffer = fs.readFileSync(options.imagePath);
    const imageBase64 = imageBuffer.toString('base64');

    // 构建请求体
    const body: Record<string, any> = {
      req_key: 'jimeng_i2i_seed3_tilesr_cvtob',
      image_base64: imageBase64
    };

    // 添加目标尺寸
    if (options.targetWidth) {
      body.width = options.targetWidth;
    }
    if (options.targetHeight) {
      body.height = options.targetHeight;
    }

    // 添加提示词
    if (options.prompt) {
      body.prompt = options.prompt;
    }

    // 提交任务
    console.log('提交任务...');
    const { taskId } = await submitTask(
      accessKey,
      secretKey,
      'jimeng_i2i_seed3_tilesr_cvtob',
      body
    );

    console.log(`任务已提交，TaskId: ${taskId}`);

    // 等待任务完成
    console.log('正在等待任务完成...');
    const result = await waitForTask(
      accessKey,
      secretKey,
      'jimeng_i2i_seed3_tilesr_cvtob',
      taskId
    );

    if (!result.images || result.images.length === 0) {
      throw new Error('任务完成但未生成图片');
    }

    // 保存结果
    const hash = crypto.createHash('md5').update(options.imagePath).digest('hex');
    const outputDir = path.resolve(options.outputDir, hash);
    
    if (!fs.existsSync(outputDir)) {
      fs.mkdirSync(outputDir, { recursive: true });
    }

    // 保存参数
    const paramPath = path.join(outputDir, 'param.json');
    fs.writeFileSync(paramPath, JSON.stringify({
      imagePath: options.imagePath,
      targetWidth: options.targetWidth,
      targetHeight: options.targetHeight,
      prompt: options.prompt,
      req_key: 'jimeng_i2i_seed3_tilesr_cvtob',
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
      const imagePath = path.join(outputDir, `outpaint_${i + 1}.jpg`);
      
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
      imagePath: options.imagePath,
      targetWidth: options.targetWidth,
      targetHeight: options.targetHeight,
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
