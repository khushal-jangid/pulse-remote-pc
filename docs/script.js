// PulseRemote Landing Page Interactive Script
document.addEventListener('DOMContentLoaded', () => {
  console.log('PulseRemote Landing Page Loaded Successfully!');

  const dlBtn = document.getElementById('btn-download-installer');
  if (dlBtn) {
    dlBtn.addEventListener('click', () => {
      console.log('Downloading PulseRemote-Setup-v1.0.exe...');
    });
  }
});
