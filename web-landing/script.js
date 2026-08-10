// 3D Interactive & Tilt Animations Script for PulseRemote Landing Page
document.addEventListener('DOMContentLoaded', () => {

  /* 1. DYNAMIC 3D CARD TILT EFFECT */
  const tiltCards = document.querySelectorAll('.tilt-card');

  tiltCards.forEach(card => {
    card.addEventListener('mousemove', (e) => {
      const rect = card.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;

      const centerX = rect.width / 2;
      const centerY = rect.height / 2;

      const rotateX = ((y - centerY) / centerY) * -12;
      const rotateY = ((x - centerX) / centerX) * 12;

      card.style.transform = `perspective(1000px) rotateX(${rotateX.toFixed(2)}deg) rotateY(${rotateY.toFixed(2)}deg) scale3d(1.02, 1.02, 1.02)`;
    });

    card.addEventListener('mouseleave', () => {
      card.style.transform = 'perspective(1000px) rotateX(0deg) rotateY(0deg) scale3d(1, 1, 1)';
    });
  });

  /* 2. INTERACTIVE 3D TOUCHPAD SIMULATOR */
  const touchpad = document.getElementById('sim-touchpad');
  const cursor = document.getElementById('sim-cursor');
  const btnLeft = document.getElementById('sim-left-btn');
  const btnRight = document.getElementById('sim-right-btn');

  if (touchpad && cursor) {
    touchpad.addEventListener('mousemove', (e) => {
      const rect = touchpad.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;

      cursor.style.left = `${x}px`;
      cursor.style.top = `${y}px`;
    });

    touchpad.addEventListener('click', (e) => {
      triggerRipple(e.clientX, e.clientY);
    });

    if (btnLeft) {
      btnLeft.addEventListener('click', (e) => {
        cursor.style.transform = 'translate(-50%, -50%) scale(1.6)';
        setTimeout(() => cursor.style.transform = 'translate(-50%, -50%) scale(1)', 150);
      });
    }

    if (btnRight) {
      btnRight.addEventListener('click', (e) => {
        cursor.style.transform = 'translate(-50%, -50%) scale(0.6)';
        setTimeout(() => cursor.style.transform = 'translate(-50%, -50%) scale(1)', 150);
      });
    }
  }

  function triggerRipple(clientX, clientY) {
    if (!touchpad) return;
    const rect = touchpad.getBoundingClientRect();
    const ripple = document.createElement('div');
    ripple.className = 'sim-ripple';
    ripple.style.cssText = `
      position: absolute;
      left: ${clientX - rect.left}px;
      top: ${clientY - rect.top}px;
      width: 10px; height: 10px;
      border-radius: 50%;
      border: 2px solid #6366f1;
      transform: translate(-50%, -50%);
      pointer-events: none;
      animation: rippleAnim 0.5s ease-out forwards;
    `;
    touchpad.appendChild(ripple);
    setTimeout(() => ripple.remove(), 500);
  }

  // Keyframe for ripple
  const style = document.createElement('style');
  style.innerHTML = `
    @keyframes rippleAnim {
      from { width: 10px; height: 10px; opacity: 1; border-color: #6366f1; }
      to { width: 120px; height: 120px; opacity: 0; border-color: #10b981; }
    }
  `;
  document.head.appendChild(style);
});
