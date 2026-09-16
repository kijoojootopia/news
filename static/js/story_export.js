document.addEventListener('DOMContentLoaded', () => {
    const exportBtn = document.getElementById('export-story-btn');
    if (!exportBtn) return;

    exportBtn.addEventListener('click', async () => {
        const target = document.getElementById('story-canvas');
        if (!target) return;

        exportBtn.disabled = true;
        const originalText = exportBtn.innerText;
        exportBtn.innerText = '저장 중...';

        try {
            // 화면 밖 스토리 캔버스를 임시 활성화
            target.style.display = 'block';

            const dataUrl = await htmlToImage.toPng(target, {
                width: 1080,
                height: 1920,
                pixelRatio: 1,
                quality: 0.95
            });

            target.style.display = 'none';

            // 이미지 자동 다운로드 트리거
            const link = document.createElement('a');
            link.download = `haru_story_${new Date().toISOString().slice(0,10)}.png`;
            link.href = dataUrl;
            link.click();
        } catch (err) {
            console.error('스토리 이미지 생성 실패:', err);
            alert('이미지 저장 중 문제가 발생했습니다.');
        } finally {
            exportBtn.disabled = false;
            exportBtn.innerText = originalText;
        }
    });
});