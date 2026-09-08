/**
 * Phòng Khám Thiện Nhân — Main JS
 * Designed by Nguyễn Quang Huy
 */

'use strict';

/* ================================================================
   UTILS
   ================================================================ */
const $ = (sel, ctx = document) => ctx.querySelector(sel);
const $$ = (sel, ctx = document) => [...ctx.querySelectorAll(sel)];
const on = (el, ev, fn, opts) => el && el.addEventListener(ev, fn, opts);

/* ================================================================
   1. PRELOADER
   ================================================================ */
function initPreloader() {
  const loader = $('#preloader');
  if (!loader) return;

  const hide = () => {
    loader.classList.add('hidden');
    document.body.style.overflow = '';
  };

  document.body.style.overflow = 'hidden';

  if (document.readyState === 'complete') {
    setTimeout(hide, 600);
  } else {
    on(window, 'load', () => setTimeout(hide, 600));
  }
}

/* ================================================================
   2. STICKY HEADER + ACTIVE NAV LINK
   ================================================================ */
function initHeader() {
  const header = $('#header');
  if (!header) return;

  const sections = $$('section[id], div[id]').filter(el =>
    $$('.nav__link').some(a => a.getAttribute('href') === `#${el.id}`)
  );

  function onScroll() {
    // Sticky style
    if (window.scrollY > 60) {
      header.classList.add('scrolled');
    } else {
      header.classList.remove('scrolled');
    }

    // Active link highlight
    const scrollMid = window.scrollY + window.innerHeight / 3;
    sections.forEach(sec => {
      const link = $(`.nav__link[href="#${sec.id}"]`);
      if (!link) return;
      const top = sec.offsetTop;
      const bot = top + sec.offsetHeight;
      if (scrollMid >= top && scrollMid < bot) {
        $$('.nav__link').forEach(l => l.classList.remove('active'));
        link.classList.add('active');
      }
    });
  }

  on(window, 'scroll', onScroll, { passive: true });
  onScroll();
}

/* ================================================================
   3. MOBILE NAV TOGGLE
   ================================================================ */
function initMobileNav() {
  const toggle = $('#navToggle');
  const menu   = $('#navMenu');
  if (!toggle || !menu) return;

  toggle.addEventListener('click', () => {
    const open = menu.classList.toggle('open');
    toggle.classList.toggle('open', open);
    toggle.setAttribute('aria-expanded', String(open));
    document.body.style.overflow = open ? 'hidden' : '';
  });

  // Close on link click
  $$('.nav__link').forEach(link => {
    on(link, 'click', () => {
      menu.classList.remove('open');
      toggle.classList.remove('open');
      toggle.setAttribute('aria-expanded', 'false');
      document.body.style.overflow = '';
    });
  });

  // Close on outside click
  on(document, 'click', e => {
    if (!menu.contains(e.target) && !toggle.contains(e.target)) {
      menu.classList.remove('open');
      toggle.classList.remove('open');
      document.body.style.overflow = '';
    }
  });
}

/* ================================================================
   4. SMOOTH SCROLL for anchor links
   ================================================================ */
function initSmoothScroll() {
  on(document, 'click', e => {
    const link = e.target.closest('a[href^="#"]');
    if (!link) return;
    const target = $(link.getAttribute('href'));
    if (!target) return;
    e.preventDefault();

    const headerH = $('#header')?.offsetHeight ?? 72;
    const top = target.getBoundingClientRect().top + window.scrollY - headerH;

    window.scrollTo({ top, behavior: 'smooth' });
  });
}

/* ================================================================
   5. BACK TO TOP BUTTON
   ================================================================ */
function initBackToTop() {
  const btn = $('#backToTop');
  if (!btn) return;

  on(window, 'scroll', () => {
    btn.classList.toggle('visible', window.scrollY > 400);
  }, { passive: true });

  on(btn, 'click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));
}

/* ================================================================
   6. AOS — Animate on Scroll (custom lightweight)
   ================================================================ */
function initAOS() {
  const elements = $$('[data-aos]');
  if (!elements.length) return;

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const el = entry.target;
        const delay = parseInt(el.dataset.aosDelay ?? '0', 10);
        setTimeout(() => el.classList.add('aos-animate'), delay);
        observer.unobserve(el);
      }
    });
  }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });

  elements.forEach(el => observer.observe(el));
}

/* ================================================================
   7. STATS COUNTER ANIMATION
   ================================================================ */
function initCounters() {
  const counters = $$('.stat-item__number[data-target]');
  if (!counters.length) return;

  const easeOut = t => 1 - Math.pow(1 - t, 3);

  function animateCounter(el) {
    const target   = parseInt(el.dataset.target, 10);
    const duration = 2000;
    const start    = performance.now();

    function tick(now) {
      const elapsed  = now - start;
      const progress = Math.min(elapsed / duration, 1);
      const value    = Math.round(easeOut(progress) * target);
      el.textContent = value.toLocaleString('vi-VN');
      if (progress < 1) requestAnimationFrame(tick);
      else el.textContent = target.toLocaleString('vi-VN');
    }

    requestAnimationFrame(tick);
  }

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        animateCounter(entry.target);
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.5 });

  counters.forEach(el => observer.observe(el));
}

/* ================================================================
   8. PARTICLE CANVAS (Hero background dots)
   ================================================================ */
function initParticles() {
  const container = $('#particles');
  if (!container) return;

  const canvas  = document.createElement('canvas');
  const ctx     = canvas.getContext('2d');
  container.appendChild(canvas);

  let W, H, particles = [];

  const PARTICLE_COUNT = window.innerWidth < 768 ? 40 : 80;
  const SPEED          = 0.4;
  const MAX_RADIUS     = 2.5;
  const CONNECTION_DIST = 120;

  class Particle {
    constructor() { this.reset(true); }
    reset(init = false) {
      this.x  = Math.random() * W;
      this.y  = init ? Math.random() * H : H + 10;
      this.r  = Math.random() * MAX_RADIUS + 0.5;
      this.vx = (Math.random() - 0.5) * SPEED;
      this.vy = -(Math.random() * SPEED + 0.2);
      this.alpha = Math.random() * 0.5 + 0.15;
    }
    update() {
      this.x += this.vx;
      this.y += this.vy;
      if (this.y < -10) this.reset();
      if (this.x < -10) this.x = W + 10;
      if (this.x > W + 10) this.x = -10;
    }
    draw() {
      ctx.beginPath();
      ctx.arc(this.x, this.y, this.r, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(255,255,255,${this.alpha})`;
      ctx.fill();
    }
  }

  function resize() {
    W = canvas.width  = container.offsetWidth;
    H = canvas.height = container.offsetHeight;
  }

  function drawConnections() {
    for (let i = 0; i < particles.length; i++) {
      for (let j = i + 1; j < particles.length; j++) {
        const dx   = particles[i].x - particles[j].x;
        const dy   = particles[i].y - particles[j].y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < CONNECTION_DIST) {
          const alpha = (1 - dist / CONNECTION_DIST) * 0.12;
          ctx.beginPath();
          ctx.moveTo(particles[i].x, particles[i].y);
          ctx.lineTo(particles[j].x, particles[j].y);
          ctx.strokeStyle = `rgba(255,255,255,${alpha})`;
          ctx.lineWidth   = 0.5;
          ctx.stroke();
        }
      }
    }
  }

  function loop() {
    ctx.clearRect(0, 0, W, H);
    drawConnections();
    particles.forEach(p => { p.update(); p.draw(); });
    requestAnimationFrame(loop);
  }

  resize();
  particles = Array.from({ length: PARTICLE_COUNT }, () => new Particle());
  loop();

  on(window, 'resize', () => { resize(); }, { passive: true });
}

/* ================================================================
   9. TESTIMONIALS SLIDER (mobile carousel dots)
   ================================================================ */
function initTestimonials() {
  const track = $('#testimonialTrack');
  const dots  = $$('#testimonialDots .testimonials__dot');
  if (!track || !dots.length) return;

  let current = 0;
  let autoTimer;

  function goTo(index) {
    const cards = $$('.testimonial-card', track);
    // On mobile (single column) we show/hide with opacity trick
    if (window.innerWidth > 768) return; // grid handles it on desktop

    current = index;
    cards.forEach((card, i) => {
      card.style.display = i === index ? 'block' : 'none';
    });
    dots.forEach((dot, i) => dot.classList.toggle('active', i === index));
  }

  function startAuto() {
    autoTimer = setInterval(() => {
      const cards = $$('.testimonial-card', track);
      goTo((current + 1) % cards.length);
    }, 4500);
  }

  function stopAuto() { clearInterval(autoTimer); }

  dots.forEach((dot, i) => {
    on(dot, 'click', () => {
      stopAuto();
      goTo(i);
      startAuto();
    });
  });

  // Touch swipe support
  let touchStartX = 0;
  on(track, 'touchstart', e => { touchStartX = e.changedTouches[0].clientX; }, { passive: true });
  on(track, 'touchend', e => {
    const diff = touchStartX - e.changedTouches[0].clientX;
    const cards = $$('.testimonial-card', track);
    if (Math.abs(diff) > 50) {
      stopAuto();
      goTo(diff > 0
        ? (current + 1) % cards.length
        : (current - 1 + cards.length) % cards.length
      );
      startAuto();
    }
  }, { passive: true });

  // Init mobile view
  function handleResize() {
    const cards = $$('.testimonial-card', track);
    const dotsEl = document.querySelector('.testimonials__dots');
    if (window.innerWidth <= 768) {
      cards.forEach((c, i) => { c.style.display = i === current ? 'block' : 'none'; });
      if (dotsEl) dotsEl.style.display = 'flex';
      startAuto();
    } else {
      cards.forEach(c => { c.style.display = ''; });
      if (dotsEl) dotsEl.style.display = 'none';
      stopAuto();
    }
  }

  on(window, 'resize', handleResize, { passive: true });
  handleResize();
}

/* ================================================================
   10. BOOKING FORM — Validation & Submit
   ================================================================ */
function initBookingForm() {
  const form      = $('#bookingForm');
  const submitBtn = $('#submitBtn');
  const modal     = $('#successModal');
  const closeBtn  = $('#modalClose');
  const overlay   = $('#modalOverlay');

  if (!form) return;

  // Set min date to today
  const dateInput = $('#date');
  if (dateInput) {
    const today = new Date().toISOString().split('T')[0];
    dateInput.setAttribute('min', today);
  }

  function showError(input) {
    input.classList.add('error');
    input.closest('.form-input-wrapper').classList.add('has-error');
  }

  function clearError(input) {
    input.classList.remove('error');
    input.closest('.form-input-wrapper')?.classList.remove('has-error');
  }

  function validate() {
    let valid = true;
    const required = $$('[required]', form);

    required.forEach(field => {
      clearError(field);
      if (!field.value.trim()) {
        showError(field);
        valid = false;
      }
    });

    // Phone validation
    const phone = $('#phone');
    if (phone && phone.value) {
      const phoneRegex = /^(0|\+84)[3-9]\d{8}$/;
      if (!phoneRegex.test(phone.value.replace(/\s/g, ''))) {
        showError(phone);
        valid = false;
      }
    }

    return valid;
  }

  // Live clear on input
  $$('input, select, textarea', form).forEach(field => {
    on(field, 'input', () => clearError(field));
    on(field, 'change', () => clearError(field));
  });

  // Submit
  on(form, 'submit', async e => {
    e.preventDefault();
    if (!validate()) {
      // Shake the form
      form.classList.add('shake');
      setTimeout(() => form.classList.remove('shake'), 500);
      return;
    }

    // Simulate loading
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Đang xử lý...';

    await new Promise(r => setTimeout(r, 1200));

    submitBtn.disabled = false;
    submitBtn.innerHTML = '<i class="fas fa-paper-plane"></i> Xác Nhận Đặt Lịch';

    form.reset();
    showModal();
  });

  function showModal() {
    modal?.classList.add('active');
    document.body.style.overflow = 'hidden';
  }

  function hideModal() {
    modal?.classList.remove('active');
    document.body.style.overflow = '';
  }

  on(closeBtn,  'click',   hideModal);
  on(overlay,   'click',   hideModal);
  on(document, 'keydown', e => { if (e.key === 'Escape') hideModal(); });
}

/* ================================================================
   11. RIPPLE EFFECT on buttons
   ================================================================ */
function initRipple() {
  on(document, 'click', e => {
    const btn = e.target.closest('.btn--primary');
    if (!btn) return;

    const rect   = btn.getBoundingClientRect();
    const size   = Math.max(rect.width, rect.height);
    const x      = e.clientX - rect.left - size / 2;
    const y      = e.clientY - rect.top  - size / 2;

    const ripple = document.createElement('span');
    Object.assign(ripple.style, {
      position: 'absolute',
      width:    `${size}px`,
      height:   `${size}px`,
      left:     `${x}px`,
      top:      `${y}px`,
      borderRadius: '50%',
      background: 'rgba(255,255,255,0.35)',
      transform: 'scale(0)',
      animation: 'rippleAnim .6s linear',
      pointerEvents: 'none',
    });

    // Ensure btn is relative
    if (getComputedStyle(btn).position === 'static') {
      btn.style.position = 'relative';
    }
    btn.style.overflow = 'hidden';
    btn.appendChild(ripple);
    setTimeout(() => ripple.remove(), 650);
  });

  // Inject keyframes once
  if (!document.getElementById('rippleStyle')) {
    const style = document.createElement('style');
    style.id = 'rippleStyle';
    style.textContent = `
      @keyframes rippleAnim {
        to { transform: scale(3); opacity: 0; }
      }
      .shake {
        animation: shakeAnim .4s ease;
      }
      @keyframes shakeAnim {
        0%,100% { transform: translateX(0); }
        20%      { transform: translateX(-8px); }
        40%      { transform: translateX( 8px); }
        60%      { transform: translateX(-5px); }
        80%      { transform: translateX( 5px); }
      }
    `;
    document.head.appendChild(style);
  }
}

/* ================================================================
   12. SERVICE CARDS — Hover tilt effect
   ================================================================ */
function initCardTilt() {
  if (window.matchMedia('(hover: none)').matches) return;

  $$('.service-card, .doctor-card').forEach(card => {
    on(card, 'mousemove', e => {
      const rect   = card.getBoundingClientRect();
      const x      = (e.clientX - rect.left) / rect.width  - 0.5;
      const y      = (e.clientY - rect.top)  / rect.height - 0.5;
      card.style.transform = `perspective(800px) rotateY(${x * 6}deg) rotateX(${-y * 6}deg) translateY(-8px)`;
    });

    on(card, 'mouseleave', () => {
      card.style.transform = '';
      card.style.transition = 'transform .4s ease';
      setTimeout(() => { card.style.transition = ''; }, 400);
    });
  });
}

/* ================================================================
   13. NAV — Scroll progress indicator
   ================================================================ */
function initScrollProgress() {
  const bar = document.createElement('div');
  Object.assign(bar.style, {
    position: 'fixed',
    top: '0',
    left: '0',
    height: '3px',
    width: '0%',
    background: 'linear-gradient(90deg, #0ea5e9, #10b981)',
    zIndex: '9999',
    transition: 'width .1s linear',
    pointerEvents: 'none',
  });
  document.body.appendChild(bar);

  on(window, 'scroll', () => {
    const docH   = document.documentElement.scrollHeight - window.innerHeight;
    const pct    = docH > 0 ? (window.scrollY / docH) * 100 : 0;
    bar.style.width = `${pct}%`;
  }, { passive: true });
}

/* ================================================================
   14. FLOATING CTA — Hide on hero, show after
   ================================================================ */
function initFloatingCTA() {
  const cta = $('.floating-cta');
  if (!cta) return;

  const hero = $('#hero');
  if (!hero) return;

  function check() {
    const heroBottom = hero.offsetTop + hero.offsetHeight;
    cta.style.opacity    = window.scrollY > heroBottom - 200 ? '1' : '0';
    cta.style.visibility = window.scrollY > heroBottom - 200 ? 'visible' : 'hidden';
  }

  Object.assign(cta.style, { transition: 'opacity .3s ease, visibility .3s ease' });
  on(window, 'scroll', check, { passive: true });
  check();
}

/* ================================================================
   15. TYPING ANIMATION on hero subtitle (optional flair)
   ================================================================ */
function initHeroTyping() {
  const badge = $('.hero__badge span');
  if (!badge) return;

  const phrases = [
    'Phòng khám uy tín hàng đầu',
    'Chăm sóc tận tâm, chuyên nghiệp',
    'Sức khỏe của bạn là ưu tiên',
  ];
  let pi = 0, ci = 0, deleting = false;

  function tick() {
    const phrase  = phrases[pi];
    const current = badge.textContent;

    if (!deleting && ci <= phrase.length) {
      badge.textContent = phrase.slice(0, ci++);
      setTimeout(tick, 60);
    } else if (!deleting && ci > phrase.length) {
      deleting = true;
      setTimeout(tick, 2000);
    } else if (deleting && ci > 0) {
      badge.textContent = phrase.slice(0, --ci);
      setTimeout(tick, 35);
    } else {
      deleting = false;
      pi = (pi + 1) % phrases.length;
      setTimeout(tick, 300);
    }
  }

  setTimeout(tick, 1500);
}

/* ================================================================
   16. LAZY-LOAD IMAGES (future-proof for real images)
   ================================================================ */
function initLazyImages() {
  const imgs = $$('img[data-src]');
  if (!imgs.length) return;

  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const img = entry.target;
        img.src = img.dataset.src;
        img.removeAttribute('data-src');
        observer.unobserve(img);
      }
    });
  }, { rootMargin: '200px' });

  imgs.forEach(img => observer.observe(img));
}

/* ================================================================
   INIT — DOMContentLoaded
   ================================================================ */
document.addEventListener('DOMContentLoaded', () => {
  initPreloader();
  initHeader();
  initMobileNav();
  initSmoothScroll();
  initBackToTop();
  initAOS();
  initCounters();
  initParticles();
  initTestimonials();
  initBookingForm();
  initRipple();
  initCardTilt();
  initScrollProgress();
  initFloatingCTA();
  initHeroTyping();
  initLazyImages();
});
