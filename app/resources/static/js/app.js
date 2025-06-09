class JOICodeGenerator {
    constructor() {
        this.form = document.getElementById('codeForm');
        this.generateBtn = document.getElementById('generateBtn');
        this.resultDiv = document.getElementById('result');
        this.errorDiv = document.getElementById('error');
        this.copyBtn = document.getElementById('copyBtn');
        
        this.init();
    }
    
    init() {
        this.updateCurrentTime();
        this.bindEvents();
    }
    
    bindEvents() {
        this.form.addEventListener('submit', (e) => this.handleSubmit(e));
        this.copyBtn.addEventListener('click', () => this.copyResult());
    }
    
    updateCurrentTime() {
        const now = new Date();
        document.getElementById("year").value = now.getFullYear();
        document.getElementById("month").value = now.getMonth() + 1;
        document.getElementById("day").value = now.getDate();
        document.getElementById("hour").value = now.getHours();
        document.getElementById("minute").value = now.getMinutes();
        document.getElementById("second").value = now.getSeconds();
    }

    buildCurrentTimeString() {
        const pad = (n) => n.toString().padStart(2, "0");
        const y = document.getElementById("year").value;
        const m = pad(document.getElementById("month").value);
        const d = pad(document.getElementById("day").value);
        const h = pad(document.getElementById("hour").value);
        const min = pad(document.getElementById("minute").value);
        const s = pad(document.getElementById("second").value);
        return `${y}-${m}-${d} ${h}:${min}:${s}`;
    }

    
    async handleSubmit(e) {
        e.preventDefault();
        
        const formData = new FormData(this.form);
        const sentence = formData.get('sentence').trim();
        
        if (!sentence) {
            this.showError('입력 문장을 입력해주세요.');
            return;
        }
        
        this.setLoading(true);
        this.hideMessages();
        
        try {
            const connectedDevicesText = formData.get('connectedDevices').trim();
            let connectedDevices = {};
            
            if (connectedDevicesText) {
                try {
                    connectedDevices = JSON.parse(connectedDevicesText);
                } catch (e) {
                    throw new Error('연결된 디바이스 JSON 형식이 올바르지 않습니다.');
                }
            }
            
            const payload = {
                sentence: sentence,
                model: "qwenCoder",
                connected_devices: connectedDevices,
                current_time: this.buildCurrentTimeString(),
                other_params: null
            };
            
            const response = await fetch('/generate_joi_code', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            
            if (!response.ok) {
                throw new Error(`서버 오류: ${response.status} - ${response.statusText}`);
            }
            
            const result = await response.json();
            this.showResult(result);
            
        } catch (error) {
            this.showError(error.message);
        } finally {
            this.setLoading(false);
        }
    }
    
    setLoading(isLoading) {
        const btnText = this.generateBtn.querySelector('.btn-text');
        const spinner = this.generateBtn.querySelector('.spinner');
        
        if (isLoading) {
            btnText.style.display = 'none';
            spinner.style.display = 'inline';
            this.generateBtn.disabled = true;
        } else {
            btnText.style.display = 'inline';
            spinner.style.display = 'none';
            this.generateBtn.disabled = false;
        }
    }
    
    showResult(result) {
        document.getElementById('generatedCode').textContent = JSON.stringify(result, null, 2);
        this.resultDiv.style.display = 'block';
        this.resultDiv.scrollIntoView({ behavior: 'smooth' });
    }
    
    showError(message) {
        document.getElementById('errorMessage').textContent = message;
        this.errorDiv.style.display = 'block';
    }
    
    hideMessages() {
        this.resultDiv.style.display = 'none';
        this.errorDiv.style.display = 'none';
    }
    
    async copyResult() {
        const code = document.getElementById('generatedCode').textContent;
        try {
            await navigator.clipboard.writeText(code);
            
            const originalText = this.copyBtn.textContent;
            this.copyBtn.textContent = '복사됨!';
            setTimeout(() => {
                this.copyBtn.textContent = originalText;
            }, 2000);
        } catch (err) {
            console.error('복사 실패:', err);
        }
    }
}

// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', () => {
    new JOICodeGenerator();
});
