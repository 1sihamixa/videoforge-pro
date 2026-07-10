// Social Proof Notifications
$(document).ready(function() {
    var names = ['سارة', 'مريم', 'نورة', 'فاطمة', 'خديجة', 'أمينة', 'حنان', 'ليلى', 'عائشة', 'سلمى', 'وفاء', 'إيمان', 'حياة', 'جميلة', 'نبيلة', 'محمد', 'أحمد', 'يوسف', 'عمر', 'خالد', 'عبدالله', 'حمزة', 'علي', 'إسماعيل', 'آدم'];
    var cities = ['الدار البيضاء', 'الرباط', 'مراكش', 'فاس', 'طنجة', 'أكادير', 'مكناس', 'وجدة', 'تطوان', 'سلا'];
    var products = ['Oud Royale', 'Rose Marocaine', 'Jasmin Blanc', 'Musk Oriental', 'Amber Dreams', 'Musk White', 'Homme Noir', 'Homme Sport', 'Musk White Pure', 'Safari'];
    var packs = ['الباقة العائلية', 'طقم رومانسي للزوجين', 'طقم عود للزوجين', 'باقة أحلام تريو', 'باقة اكتشاف', 'طقم هدايا ملكي'];

    function showNotification() {
        var isMale = ['محمد', 'أحمد', 'يوسف', 'عمر', 'خالد', 'عبدالله', 'حمزة', 'علي', 'إسماعيل', 'آدم'].includes(name);
        var verb = isMale ? 'اشترى' : 'اشترت';
        var isPack = Math.random() < 0.3;
        var item;
        if (isPack && Math.random() < 0.5) {
            var qty = Math.floor(Math.random() * 3) + 2;
            var prod = products[Math.floor(Math.random() * products.length)];
            item = qty + ' عطور (' + prod + ' + ' + (qty - 1) + ' أخرى)';
        } else if (isPack) {
            item = packs[Math.floor(Math.random() * packs.length)];
        } else {
            item = products[Math.floor(Math.random() * products.length)];
        }
        var time = Math.floor(Math.random() * 12) + 2;
        var emoji = ['🛒', '💝', '✨', '🎀', '👌', '🔥', '💎'][Math.floor(Math.random() * 7)];

        var $note = $(
            '<div class="social-notification">' +
                '<span class="sn-emoji">' + emoji + '</span>' +
                '<span class="sn-text"><strong>' + name + '</strong> من ' + city + ' ' + verb + ' <strong>' + item + '</strong></span>' +
                '<span class="sn-time">قبل ' + time + ' دقائق</span>' +
            '</div>'
        );

        $('body').append($note);

        // Slide in
        setTimeout(function() {
            $note.addClass('show');
        }, 100);

        // Remove after 5 seconds
        setTimeout(function() {
            $note.removeClass('show');
            setTimeout(function() { $note.remove(); }, 500);
        }, 5000);
    }

    // First notification after 3 seconds
    setTimeout(function() {
        showNotification();
    }, 3000);

    // Repeat every 8-15 seconds
    setInterval(function() {
        showNotification();
    }, 8000 + Math.random() * 7000);

    // Low stock badge animation
    $('.low-stock').each(function() {
        var count = parseInt($(this).data('count'));
        if (count <= 3) {
            $(this).addClass('critical');
        }
    });

    // Cart popup close
    $(document).on('click', '#cart-popup .close-popup, #cart-popup .popup-overlay', function() {
        $('#cart-popup').fadeOut(200);
    });

    // ─── AJAX Search ─────────────────────────────
    var searchTimeout;
    $('.search-input').on('input', function() {
        var q = $(this).val().trim();
        clearTimeout(searchTimeout);
        if (q.length < 2) {
            $('.search-results').html('');
            return;
        }
        searchTimeout = setTimeout(function() {
            $.getJSON('/api/search?q=' + encodeURIComponent(q), function(data) {
                var html = '';
                if (data.results && data.results.length > 0) {
                    $.each(data.results, function(i, r) {
                        html += '<a href="' + r.url + '" class="search-result-item">' +
                            '<img src="' + r.image + '" alt="' + r.name + '">' +
                            '<div class="search-result-info">' +
                                '<h4>' + r.name + '</h4>' +
                                '<span>' + (r.gender == 'male' ? 'رجالي' : r.gender == 'female' ? 'نسائي' : 'للجنسين') + '</span>' +
                            '</div>' +
                            '<span class="search-result-price">' + r.price + ' درهم</span>' +
                        '</a>';
                    });
                } else {
                    html = '<div class="search-empty"><i class="fas fa-search"></i><p>لا توجد نتائج</p></div>';
                }
                $('.search-results').html(html);
            });
        }, 300);
    });

    // ─── Wishlist Toggle ──────────────────────────
    $(document).on('click', '.wishlist-toggle', function(e) {
        e.preventDefault();
        var $btn = $(this);
        var pid = $btn.data('product-id');
        $.post('/wishlist/toggle/' + pid, function(data) {
            if (data.in_wishlist) {
                $btn.addClass('in-wishlist').html('<i class="fas fa-heart"></i>');
            } else {
                $btn.removeClass('in-wishlist').html('<i class="far fa-heart"></i>');
            }
        });
    });

    // ─── Quiz Navigation ─────────────────────────
    $('#quiz-next').click(function() {
        var $current = $('.quiz-step.active');
        var step = parseInt($current.data('step'));
        // Validate current step has a selected radio
        var $checked = $current.find('input[type="radio"]:checked');
        if ($checked.length === 0) {
            $current.find('.quiz-option').first().css('border-color', 'var(--red)');
            setTimeout(function() { $current.find('.quiz-option').first().css('border-color', ''); }, 1000);
            return;
        }
        var $next = $('.quiz-step[data-step="' + (step + 1) + '"]');
        if ($next.length) {
            $current.removeClass('active');
            $next.addClass('active');
            $('#quiz-prev').show();
            if ($next.data('step') === 5) {
                $('#quiz-next').hide();
                $('#quiz-submit').show();
            }
        }
        $('html, body').animate({ scrollTop: $('.quiz-container').offset().top - 100 }, 300);
    });

    $('#quiz-prev').click(function() {
        var $current = $('.quiz-step.active');
        var step = parseInt($current.data('step'));
        var $prev = $('.quiz-step[data-step="' + (step - 1) + '"]');
        if ($prev.length) {
            $current.removeClass('active');
            $prev.addClass('active');
            $('#quiz-submit').hide();
            $('#quiz-next').show();
            if ($prev.data('step') === 1) {
                $('#quiz-prev').hide();
            }
        }
        $('html, body').animate({ scrollTop: $('.quiz-container').offset().top - 100 }, 300);
    });

    // ─── Search Modal ─────────────────────────────
    $(document).on('click', '.search-trigger', function(e) {
        e.preventDefault();
        $('.search-overlay, .search-modal').addClass('open');
        $('.search-input').focus();
    });
    $(document).on('click', '.close-search, .search-overlay', function() {
        $('.search-overlay, .search-modal').removeClass('open');
    });
    $(document).on('keydown', function(e) {
        if (e.key === 'Escape') {
            $('.search-overlay, .search-modal').removeClass('open');
        }
    });
    // Ctrl+K / Cmd+K shortcut
    $(document).on('keydown', function(e) {
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            $('.search-overlay, .search-modal').addClass('open');
            $('.search-input').focus();
        }
    });
});

// Cart popup trigger
function showCartPopup(data) {
    $('#cart-popup .popup-product-name').text(data.name);
    $('#cart-popup .popup-product-price').text(data.price);
    $('#cart-popup .suggestions-grid').html(data.suggestions);
    $('#cart-popup').fadeIn(300);
    setTimeout(function() {
        $('#cart-popup').fadeOut(300);
    }, 8000);
}

// Countdown Timer (daily flash sale)
function initCountdown() {
    var $timer = $('#flash-timer');
    if (!$timer.length) return;
    var end = new Date();
    end.setHours(23, 59, 59, 0);
    function tick() {
        var now = new Date();
        var diff = end - now;
        if (diff <= 0) { $timer.html('انتهى العرض'); return; }
        var h = Math.floor(diff / 3600000);
        var m = Math.floor((diff % 3600000) / 60000);
        var s = Math.floor((diff % 60000) / 1000);
        $timer.html(
            '<span>' + String(h).padStart(2,'0') + '</span>:' +
            '<span>' + String(m).padStart(2,'0') + '</span>:' +
            '<span>' + String(s).padStart(2,'0') + '</span>'
        );
    }
    tick();
    setInterval(tick, 1000);
}
initCountdown();

// AJAX Add to Cart
$(document).on('submit', '.add-to-cart-form', function(e) {
    e.preventDefault();
    var $form = $(this);
    var $btn = $form.find('button[type="submit"]');
    var originalText = $btn.html();

    $btn.html('<i class="fas fa-spinner fa-spin"></i> جار الإضافة...').prop('disabled', true);

    $.ajax({
        url: $form.attr('action'),
        method: 'POST',
        data: $form.serialize(),
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
        success: function(data) {
            if (data.success) {
                showCartPopup(data);
                // Update cart count badge
                $.get('/cart/count', function(count) {
                    var $badge = $('.cart-icon .badge');
                    var c = parseInt(count);
                    if (c > 0) {
                        if ($badge.length) $badge.text(c);
                        else $('.cart-icon').append('<span class="badge">' + c + '</span>');
                    } else {
                        $badge.remove();
                    }
                });
            }
        },
        error: function() {
            // Fallback: submit normally
            $form.off('submit').submit();
        },
        complete: function() {
            $btn.html(originalText).prop('disabled', false);
        }
    });
});
