// imageProcessor.js
self.addEventListener('message', async (e) => {
    try {
        const { file, maxWidth, maxHeight, quality } = e.data;
        const bitmap = await createImageBitmap(file);

        // 计算缩放比例
        const scale = Math.min(
            maxWidth / bitmap.width,
            maxHeight / bitmap.height,
            1
        );

        // 创建画布进行压缩
        const canvas = new OffscreenCanvas(
            bitmap.width * scale,
            bitmap.height * scale
        );
        const ctx = canvas.getContext('2d');
        ctx.drawImage(bitmap, 0, 0, canvas.width, canvas.height);

        // 转换为Blob
        const blob = await canvas.convertToBlob({
            type: 'image/jpeg',
            quality: quality
        });

        self.postMessage({ result: blob });
    } catch (error) {
        self.postMessage({ error: error.message });
    }
});