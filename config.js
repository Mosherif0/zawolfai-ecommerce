/**
 * CartWise Frontend — API Configuration
 * 
 * مكان واحد لكل الـAPI URLs. لو غيرت بورت أو مسار، من هنا بس.
 * 
 * الخدمات:
 *   - recommendations: port 8100 (catalog, search, related items)
 *   - ocr: port 8200 (receipt upload, inventory)
 *   - chatbot: port 8300 (RAG assistant)
 *   - forecasting: port 8400 (demand prediction)
 */

const API_CONFIG = {
    recommendations: 'http://127.0.0.1:8100',
    ocr: 'http://127.0.0.1:8200',
    chatbot: 'http://127.0.0.1:8300',
    forecasting: 'http://127.0.0.1:8400',
};

// Helper: build full URL
function apiUrl(service, path) {
    return API_CONFIG[service] + path;
}
