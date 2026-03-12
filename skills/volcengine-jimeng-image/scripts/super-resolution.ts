#!/usr/bin/env ts-node
/**
 * 高清放大脚本 - Super Resolution
 * 提升图片分辨率
 *
 * 用法：ts-node super-resolution.ts <图片路径> [选项]
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

interface SuperResolutionOptions {
  imagePath: string;
  scale: number;
  outputDir: string;
  download: boolean;
  debug: boolean;
}

function parseArgs(): SuperResolutionOptions {
  const args = process.argv.slice(2);

  if (args.length < 1) {
    console.error('用法：ts-node super-resolution.ts <图片路径> [选项]');
    console.error('');
    console.error('选项:');
    console.error('  --scale <倍数>           放大倍数 2/4 (默认：2)');
    console.error('  --output <目录>          图片下载目录 (默认：./output)');
    console.error('  --no-download            不下载图片，只返回 URL');
    console.error('  --debug                  开启调试模式');
    process.exit(1);
  }

  const imagePath = args[0];
  let scale = 2;
  let outputDir = './output';
  let download = true;
  let debug = false;

  for (let i = 1; i < args.length; i++) {
    switch (args[i]) {
      case '--scale':
        scale = parseInt(args[++i]);
        if (scale !== 2 && scale !== 4) {
          throw new Error('放大倍数必须为 2 或 4');
        }
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
    scale,
    outputDir,
    download,
    debug
  };
}

async function main() {
  try {
    const options = parseArgs();
    const { accessKey, secretKey } = getCredentials();

    console.log(`\n🔍 高清放大任务`);
    console.log(`原图：${options.imagePath}`);
    console.log(`放大倍数：${options.scale}x`);
    console.log('');

    // 读取原图
    const imageBuffer = fs.readFileSync(options.imagePath);
    const imageBase64 = imageBuffer.toString('base64');

    // 构建请求体
    const body: Record<string, any> = {
      req_key: 'jimeng_image_super_resolution',
      image_base64: imageBase64,
      scale: options.scale
    };

    // 提交任务
    console.log('提交任务...');
    const { taskId } = await submitTask(
      accessKey,
      secretKey,
      'jimeng_image_super_resolution',
      body
    );

    console.log(`任务已提交，TaskId: ${taskId}`);

    // 等待任务完成
    console.log('正在等待任务完成...');
    const result = await waitForTask(
      accessKey,
      secretKey,
      'jimeng_image_super_resolution',
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
      scale: options.scale,
      req_key: 'jimeng_image_super_resolution',
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
      const imagePath = path.join(outputDir, `sr_${options.scale}x_${i + 1}.jpg`);
      
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
      scale: options.scale,
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
