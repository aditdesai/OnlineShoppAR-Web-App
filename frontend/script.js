async function uploadImage(e) {
    e.preventDefault();

    if (fileUpload.files.length > 0) {
        createModelBtn.textContent = 'Creating 3D Model...';
        createModelBtn.disabled = true;

        const formData = new FormData();
        formData.append('image', fileUpload.files[0]);

        try {
            const response = await fetch('https://primate-wise-longhorn.ngrok-free.app/image-to-3d-pipeline', {
                method: 'POST',
                body: formData
            });

            if (response.ok) {
                const blob = await response.blob();
                const url = URL.createObjectURL(blob);
                arLink.href = url;
                arViewer.classList.remove('hidden');
                createModelBtn.textContent = 'Create 3D Model';
                createModelBtn.disabled = false;
            } else {
                throw new Error('Failed to create 3D model');
            }
        } catch (error) {
            console.error('Error:', error);
            createModelBtn.textContent = 'Error: Try Again';
            createModelBtn.disabled = false;
        }
    }
};

document.addEventListener('DOMContentLoaded', function() {
    const menuToggle = document.getElementById('menuToggle');
    const mobileMenu = document.getElementById('mobileMenu');
    const menuIcon = menuToggle.querySelector('i');

    menuToggle.addEventListener('click', function(e) {
        e.preventDefault();

        mobileMenu.classList.toggle('hidden');
        menuIcon.setAttribute('data-lucide', mobileMenu.classList.contains('hidden') ? 'menu' : 'x');
        lucide.createIcons();
    });

    const fileUpload = document.getElementById('fileUpload');
    const uploadText = document.getElementById('uploadText');
    const createModelBtn = document.getElementById('createModelBtn');
    const arViewer = document.getElementById('arViewer');
    const arLink = document.getElementById('arLink');

    fileUpload.addEventListener('change', function(e) {
        if (e.target.files.length > 0) {
            const fileName = e.target.files[0].name;
            uploadText.innerHTML = `
                <i data-lucide="image" class="mx-auto mb-2"></i>
                <span>${fileName}</span>
            `;
            lucide.createIcons();
            createModelBtn.classList.remove('bg-gray-300', 'text-gray-600', 'cursor-not-allowed');
            createModelBtn.classList.add('bg-blue-600', 'text-white', 'hover:bg-blue-700');
        }
    });

    

    window.openModal = function(modalId) {
        document.getElementById(modalId).classList.remove('hidden');
    }

    window.closeModal = function(modalId) {
        document.getElementById(modalId).classList.add('hidden');
    }

    window.addEventListener('click', function(e) {
        if (e.target.classList.contains('fixed')) {
            e.target.classList.add('hidden');
        }
    });

    lucide.createIcons();
});