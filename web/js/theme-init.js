try { var t = localStorage.getItem('prana-theme'); if (t) document.documentElement.dataset.theme = t; } catch (e) { /* storage unavailable: keep the default theme */ }
