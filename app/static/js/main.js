let currentFont = 'Brush Script MT, cursive';
let currentColor = '#000000';
let currentName = '';

function setFontStyle(font) {
    currentFont = font;
}

function setSignatureColor(color) {
    currentColor = color;
}

function generateSignature() {
    const nameInput = document.getElementById('name');
    currentName = nameInput.value.trim();
    
    if (!currentName) {
        alert('Please enter your name first');
        return;
    }
    
    const signatureResult = document.getElementById('signature-result');
    signatureResult.innerHTML = `
        <div class="signature-example text-3xl" style="color: ${currentColor}; font-family: ${currentFont}">
            ${currentName}
        </div>
    `;
    
    // Enable download and copy buttons
    document.getElementById('download-btn').disabled = false;
    document.getElementById('download-btn').classList.remove('opacity-50', 'cursor-not-allowed');
    document.getElementById('copy-btn').disabled = false;
    document.getElementById('copy-btn').classList.remove('opacity-50', 'cursor-not-allowed');

    // Save signature to database
    saveSignature();
}

async function saveSignature() {
    try {
        const response = await fetch('/api/signatures/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                user_id: 1, // This should be replaced with the actual logged-in user's ID
                font_style: currentFont,
                color: currentColor
            })
        });
        
        if (!response.ok) {
            throw new Error('Failed to save signature');
        }
        
        const data = await response.json();
        console.log('Signature saved:', data);
    } catch (error) {
        console.error('Error saving signature:', error);
    }
}

function downloadSignature() {
    if (!currentName) return;
    
    // Create a canvas to draw the signature
    const canvas = document.createElement('canvas');
    canvas.width = 600;
    canvas.height = 200;
    const ctx = canvas.getContext('2d');
    
    // Set font and color
    ctx.font = '40px ' + currentFont;
    ctx.fillStyle = currentColor;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    
    // Draw the text
    ctx.fillText(currentName, canvas.width / 2, canvas.height / 2);
    
    // Create download link
    const link = document.createElement('a');
    link.download = `${currentName.replace(/\s+/g, '_')}_signature.png`;
    link.href = canvas.toDataURL('image/png');
    link.click();
}

function copySignature() {
    if (!currentName) return;
    
    // Create a temporary element to hold the signature
    const tempElement = document.createElement('div');
    tempElement.style.fontFamily = currentFont;
    tempElement.style.color = currentColor;
    tempElement.style.fontSize = '24px';
    tempElement.style.position = 'absolute';
    tempElement.style.left = '-9999px';
    tempElement.textContent = currentName;
    document.body.appendChild(tempElement);
    
    // Select the text
    const range = document.createRange();
    range.selectNode(tempElement);
    window.getSelection().removeAllRanges();
    window.getSelection().addRange(range);
    
    // Copy the text
    try {
        document.execCommand('copy');
        alert('Signature copied to clipboard!');
    } catch (err) {
        alert('Failed to copy signature');
    }
    
    // Clean up
    window.getSelection().removeAllRanges();
    document.body.removeChild(tempElement);
} 