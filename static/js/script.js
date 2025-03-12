document.addEventListener('DOMContentLoaded', function() {
    // Load languages for dropdowns
    fetchLanguages();
    
    // Add event listener for the add field button
    const addFieldBtn = document.getElementById('add-field-btn');
    if (addFieldBtn) {
        addFieldBtn.addEventListener('click', addCustomField);
    }
    
    // Add loading overlay when form is submitted
    const form = document.querySelector('form');
    if (form) {
        form.addEventListener('submit', function() {
            showLoadingOverlay();
        });
    }
    
    // Add event listener for API selection to show appropriate language options
    const apiRadios = document.querySelectorAll('input[name="api"]');
    apiRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            fetchLanguages();
        });
    });
});

function fetchLanguages() {
    fetch('/languages')
        .then(response => response.json())
        .then(data => {
            populateLanguageSelects(data.languages);
        })
        .catch(error => {
            console.error('Error fetching languages:', error);
        });
}

function populateLanguageSelects(languages) {
    const srcLangSelect = document.getElementById('src_lang');
    const targetLangSelect = document.getElementById('target_lang');
    
    if (!srcLangSelect || !targetLangSelect) return;
    
    // Store selected values before clearing
    const selectedSrcLang = srcLangSelect.value;
    const selectedTargetLang = targetLangSelect.value;
    
    // Clear existing options except the first one
    while (srcLangSelect.options.length > 1) {
        srcLangSelect.remove(1);
    }
    
    while (targetLangSelect.options.length > 1) {
        targetLangSelect.remove(1);
    }
    
    // LibreTranslate languages - limited set
    const libreTranslateLanguages = [
        {code: 'en', name: 'English'},
        {code: 'ar', name: 'Arabic'},
        {code: 'zh', name: 'Chinese'},
        {code: 'nl', name: 'Dutch'},
        {code: 'fr', name: 'French'},
        {code: 'de', name: 'German'},
        {code: 'hi', name: 'Hindi'},
        {code: 'hu', name: 'Hungarian'},
        {code: 'id', name: 'Indonesian'},
        {code: 'ga', name: 'Irish'},
        {code: 'it', name: 'Italian'},
        {code: 'ja', name: 'Japanese'},
        {code: 'ko', name: 'Korean'},
        {code: 'pl', name: 'Polish'},
        {code: 'pt', name: 'Portuguese'},
        {code: 'ru', name: 'Russian'},
        {code: 'es', name: 'Spanish'},
        {code: 'sv', name: 'Swedish'},
        {code: 'tr', name: 'Turkish'},
        {code: 'uk', name: 'Ukrainian'},
        {code: 'vi', name: 'Vietnamese'}
    ];
    
    // Determine which API is selected
    const selectedApi = document.querySelector('input[name="api"]:checked').value;
    const languagesToUse = selectedApi === 'libretranslate' ? libreTranslateLanguages : languages;
    
    // Add languages to dropdowns
    languagesToUse.forEach(lang => {
        // Skip English in source and Russian in target as they're already added
        if (lang.code !== 'en') {
            const srcOption = document.createElement('option');
            srcOption.value = lang.code;
            srcOption.textContent = lang.name;
            srcLangSelect.appendChild(srcOption);
        }
        
        if (lang.code !== 'ru') {
            const targetOption = document.createElement('option');
            targetOption.value = lang.code;
            targetOption.textContent = lang.name;
            targetLangSelect.appendChild(targetOption);
        }
    });
    
    // Restore selected values if they're available in the new options
    if (selectedSrcLang) {
        if (Array.from(srcLangSelect.options).some(opt => opt.value === selectedSrcLang)) {
            srcLangSelect.value = selectedSrcLang;
        }
    }
    
    if (selectedTargetLang) {
        if (Array.from(targetLangSelect.options).some(opt => opt.value === selectedTargetLang)) {
            targetLangSelect.value = selectedTargetLang;
        }
    }
}

function addCustomField() {
    const customFieldsContainer = document.getElementById('custom-fields');
    const fieldCount = customFieldsContainer.children.length;
    
    const fieldRow = document.createElement('div');
    fieldRow.className = 'custom-field-row';
    fieldRow.innerHTML = `
        <input type="text" class="form-control" name="fields" placeholder="Enter field name" required>
        <button type="button" class="btn btn-outline-danger" onclick="removeCustomField(this)">
            <span aria-hidden="true">&times;</span>
        </button>
    `;
    
    customFieldsContainer.appendChild(fieldRow);
}

function removeCustomField(button) {
    const fieldRow = button.parentElement;
    fieldRow.remove();
}

function showLoadingOverlay() {
    // Create loading overlay
    const overlay = document.createElement('div');
    overlay.className = 'loading-overlay';
    overlay.innerHTML = `
        <div class="spinner-border" role="status">
            <span class="visually-hidden">Loading...</span>
        </div>
        <p class="mt-3">Translating XML... This may take a few moments.</p>
    `;
    
    document.body.appendChild(overlay);
} 