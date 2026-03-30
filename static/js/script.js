/**
 * Smart College Event Management System – JavaScript
 * Handles: form validation, navbar toggle, dynamic fields,
 * confirm popups, flash messages, and Chart.js integration.
 */

document.addEventListener('DOMContentLoaded', function () {

    // ─── Navbar Scroll Effect ────────────────────────────────
    const navbar = document.querySelector('.navbar');
    if (navbar) {
        window.addEventListener('scroll', function () {
            navbar.classList.toggle('scrolled', window.scrollY > 20);
        });
    }

    // ─── Hamburger Menu Toggle ───────────────────────────────
    const hamburger = document.querySelector('.hamburger');
    const navLinks = document.querySelector('.navbar-links');
    const mobileOverlay = document.querySelector('.mobile-overlay');

    if (hamburger && navLinks) {
        hamburger.addEventListener('click', function () {
            hamburger.classList.toggle('active');
            navLinks.classList.toggle('active');
            if (mobileOverlay) mobileOverlay.classList.toggle('active');
            document.body.style.overflow = navLinks.classList.contains('active') ? 'hidden' : '';
        });

        // Close menu when clicking overlay
        if (mobileOverlay) {
            mobileOverlay.addEventListener('click', function () {
                hamburger.classList.remove('active');
                navLinks.classList.remove('active');
                mobileOverlay.classList.remove('active');
                document.body.style.overflow = '';
            });
        }

        // Close menu when clicking a link
        navLinks.querySelectorAll('a').forEach(function (link) {
            link.addEventListener('click', function () {
                hamburger.classList.remove('active');
                navLinks.classList.remove('active');
                if (mobileOverlay) mobileOverlay.classList.remove('active');
                document.body.style.overflow = '';
            });
        });
    }

    // ─── Flash Messages Auto-Dismiss ─────────────────────────
    const flashMessages = document.querySelectorAll('.flash-message');
    flashMessages.forEach(function (msg) {
        // Auto dismiss after 5 seconds
        setTimeout(function () {
            msg.style.animation = 'slideOut 0.4s ease forwards';
            setTimeout(function () { msg.remove(); }, 400);
        }, 5000);

        // Click to dismiss
        msg.addEventListener('click', function () {
            msg.style.animation = 'slideOut 0.4s ease forwards';
            setTimeout(function () { msg.remove(); }, 400);
        });
    });

    // ─── Toggle Participant Limit Fields ─────────────────────
    const limitToggle = document.getElementById('limit_enabled');
    const limitFields = document.getElementById('limit-fields');

    if (limitToggle && limitFields) {
        function toggleLimitFields() {
            limitFields.classList.toggle('visible', limitToggle.checked);
            if (!limitToggle.checked) {
                const maxInput = document.getElementById('max_participants');
                if (maxInput) maxInput.value = '';
            }
        }
        limitToggle.addEventListener('change', toggleLimitFields);
        toggleLimitFields(); // Initialize on page load
    }

    // ─── Toggle Payment Fields ───────────────────────────────
    const paidToggle = document.getElementById('is_paid');
    const paidFields = document.getElementById('payment-fields');

    if (paidToggle && paidFields) {
        function togglePaymentFields() {
            paidFields.classList.toggle('visible', paidToggle.checked);
            if (!paidToggle.checked) {
                const priceInput = document.getElementById('price');
                const upiInput = document.getElementById('upi_id');
                if (priceInput) priceInput.value = '';
                if (upiInput) upiInput.value = '';
            }
        }
        paidToggle.addEventListener('change', togglePaymentFields);
        togglePaymentFields(); // Initialize on page load
    }

    // ─── File Upload Display ─────────────────────────────────
    document.querySelectorAll('.file-upload').forEach(function (uploadArea) {
        const input = uploadArea.querySelector('input[type="file"]');
        const fileNameEl = uploadArea.querySelector('.file-name');

        if (input) {
            uploadArea.addEventListener('click', function () {
                input.click();
            });

            input.addEventListener('change', function () {
                if (input.files.length > 0) {
                    const file = input.files[0];

                    // Validate file size (2MB)
                    if (file.size > 2 * 1024 * 1024) {
                        alert('File size exceeds 2MB limit. Please choose a smaller file.');
                        input.value = '';
                        if (fileNameEl) fileNameEl.textContent = '';
                        return;
                    }

                    // Validate file type
                    const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png'];
                    if (!allowedTypes.includes(file.type)) {
                        alert('Only JPG, JPEG, and PNG files are allowed.');
                        input.value = '';
                        if (fileNameEl) fileNameEl.textContent = '';
                        return;
                    }

                    if (fileNameEl) {
                        fileNameEl.textContent = '📎 ' + file.name;
                    }
                }
            });
        }
    });

    // ─── Registration Confirmation Popup ─────────────────────
    document.querySelectorAll('.register-form').forEach(function (form) {
        form.addEventListener('submit', function (e) {
            const eventName = form.dataset.eventName || 'this event';
            const isPaid = form.dataset.isPaid === '1';

            if (isPaid) {
                const checkbox = form.querySelector('input[name="payment_confirmed"]');
                if (checkbox && !checkbox.checked) {
                    e.preventDefault();
                    alert('Please confirm that you have completed the payment.');
                    return;
                }
            }

            if (!confirm('Are you sure you want to register for "' + eventName + '"?')) {
                e.preventDefault();
            }
        });
    });

    // ─── Delete Event Confirmation ───────────────────────────
    document.querySelectorAll('.delete-form').forEach(function (form) {
        form.addEventListener('submit', function (e) {
            if (!confirm('Are you sure you want to delete this event? This action cannot be undone.')) {
                e.preventDefault();
            }
        });
    });

    // ─── Form Validation ─────────────────────────────────────
    document.querySelectorAll('form[data-validate]').forEach(function (form) {
        form.addEventListener('submit', function (e) {
            let valid = true;

            // Check required fields
            form.querySelectorAll('[required]').forEach(function (field) {
                if (!field.value.trim()) {
                    valid = false;
                    field.style.borderColor = '#ef4444';
                    field.addEventListener('input', function () {
                        field.style.borderColor = '';
                    }, { once: true });
                }
            });

            // Check password match
            const password = form.querySelector('input[name="password"]');
            const confirm = form.querySelector('input[name="confirm_password"]');
            if (password && confirm && password.value !== confirm.value) {
                valid = false;
                confirm.style.borderColor = '#ef4444';
                alert('Passwords do not match.');
            }

            // Check password length
            if (password && password.value.length > 0 && password.value.length < 6) {
                valid = false;
                password.style.borderColor = '#ef4444';
                alert('Password must be at least 6 characters.');
            }

            // Check email format
            const email = form.querySelector('input[type="email"]');
            if (email && email.value) {
                const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
                if (!emailRegex.test(email.value)) {
                    valid = false;
                    email.style.borderColor = '#ef4444';
                    alert('Please enter a valid email address.');
                }
            }

            if (!valid) {
                e.preventDefault();
            }
        });
    });

    // ─── Event Detail Modal ──────────────────────────────────
    document.querySelectorAll('.event-detail-trigger').forEach(function (trigger) {
        trigger.addEventListener('click', function () {
            const modalId = trigger.dataset.modal;
            const modal = document.getElementById(modalId);
            if (modal) {
                modal.classList.add('active');
                document.body.style.overflow = 'hidden';
            }
        });
    });

    document.querySelectorAll('.modal-overlay').forEach(function (overlay) {
        // Close on clicking overlay (outside modal)
        overlay.addEventListener('click', function (e) {
            if (e.target === overlay) {
                overlay.classList.remove('active');
                document.body.style.overflow = '';
            }
        });

        // Close button
        overlay.querySelectorAll('.modal-close').forEach(function (btn) {
            btn.addEventListener('click', function () {
                overlay.classList.remove('active');
                document.body.style.overflow = '';
            });
        });
    });

    // Close modal on Escape key
    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') {
            document.querySelectorAll('.modal-overlay.active').forEach(function (modal) {
                modal.classList.remove('active');
                document.body.style.overflow = '';
            });
        }
    });

    // ─── Fade-in Animation Observer ──────────────────────────
    const fadeElements = document.querySelectorAll('.fade-in');
    if (fadeElements.length > 0 && 'IntersectionObserver' in window) {
        const observer = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    entry.target.style.animationPlayState = 'running';
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.1 });

        fadeElements.forEach(function (el) {
            el.style.animationPlayState = 'paused';
            observer.observe(el);
        });
    }

    // ─── Chart.js – Admin Dashboard ──────────────────────────
    const barChartCanvas = document.getElementById('participantsBarChart');
    const pieChartCanvas = document.getElementById('registrationPieChart');

    if (barChartCanvas || pieChartCanvas) {
        loadChartData();
    }

    function loadChartData() {
        fetch('/api/chart-data')
            .then(function (response) { return response.json(); })
            .then(function (data) {
                if (data.labels && data.labels.length > 0) {
                    renderBarChart(data);
                    renderPieChart(data);
                } else {
                    // Show empty state if no data
                    if (barChartCanvas) {
                        barChartCanvas.parentElement.innerHTML =
                            '<div class="empty-state"><div class="empty-icon">📊</div><p>No event data available yet.</p></div>';
                    }
                    if (pieChartCanvas) {
                        pieChartCanvas.parentElement.innerHTML =
                            '<div class="empty-state"><div class="empty-icon">📈</div><p>No registration data available yet.</p></div>';
                    }
                }
            })
            .catch(function (err) {
                console.error('Chart data error:', err);
            });
    }

    function renderBarChart(data) {
        if (!barChartCanvas) return;

        // Generate gradient colors for bars
        const ctx = barChartCanvas.getContext('2d');
        const gradient = ctx.createLinearGradient(0, 0, 0, 300);
        gradient.addColorStop(0, 'rgba(79, 70, 229, 0.8)');
        gradient.addColorStop(1, 'rgba(6, 182, 212, 0.6)');

        new Chart(barChartCanvas, {
            type: 'bar',
            data: {
                labels: data.labels,
                datasets: [{
                    label: 'Participants',
                    data: data.participants,
                    backgroundColor: generateColors(data.labels.length, 0.7),
                    borderColor: generateColors(data.labels.length, 1),
                    borderWidth: 2,
                    borderRadius: 8,
                    borderSkipped: false,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        backgroundColor: '#1e293b',
                        titleFont: { family: 'Inter', size: 13, weight: '600' },
                        bodyFont: { family: 'Inter', size: 12 },
                        padding: 12,
                        cornerRadius: 8,
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1,
                            font: { family: 'Inter', size: 12 },
                            color: '#64748b'
                        },
                        grid: { color: '#f1f5f9' }
                    },
                    x: {
                        ticks: {
                            font: { family: 'Inter', size: 11 },
                            color: '#64748b',
                            maxRotation: 45
                        },
                        grid: { display: false }
                    }
                }
            }
        });
    }

    function renderPieChart(data) {
        if (!pieChartCanvas) return;

        new Chart(pieChartCanvas, {
            type: 'doughnut',
            data: {
                labels: data.labels,
                datasets: [{
                    data: data.participants,
                    backgroundColor: generateColors(data.labels.length, 0.7),
                    borderColor: '#ffffff',
                    borderWidth: 3,
                    hoverBorderWidth: 0,
                    hoverOffset: 8,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '55%',
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 16,
                            usePointStyle: true,
                            pointStyleWidth: 10,
                            font: { family: 'Inter', size: 12 }
                        }
                    },
                    tooltip: {
                        backgroundColor: '#1e293b',
                        titleFont: { family: 'Inter', size: 13, weight: '600' },
                        bodyFont: { family: 'Inter', size: 12 },
                        padding: 12,
                        cornerRadius: 8,
                    }
                }
            }
        });
    }

    function generateColors(count, alpha) {
        const baseColors = [
            [79, 70, 229],    // Indigo
            [6, 182, 212],     // Cyan
            [124, 58, 237],    // Purple
            [16, 185, 129],    // Green
            [245, 158, 11],    // Amber
            [239, 68, 68],     // Red
            [59, 130, 246],    // Blue
            [236, 72, 153],    // Pink
            [20, 184, 166],    // Teal
            [249, 115, 22],    // Orange
        ];

        var colors = [];
        for (var i = 0; i < count; i++) {
            var c = baseColors[i % baseColors.length];
            colors.push('rgba(' + c[0] + ', ' + c[1] + ', ' + c[2] + ', ' + alpha + ')');
        }
        return colors;
    }

    // ─── Smooth Scroll for Anchor Links ──────────────────────
    document.querySelectorAll('a[href^="#"]').forEach(function (anchor) {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            var target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    });

});
