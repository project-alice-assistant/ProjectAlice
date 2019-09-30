(function () {
    let up = true;

    function startTime() {
        let today = new Date();
        let h = String(today.getHours()).padStart(2, '0');
        let m = String(today.getMinutes()).padStart(2, '0');

        if (up) {
            $('#DateDayTimeYear_clock').html(h + ':' + m);
        }
        else {
            $('#DateDayTimeYear_clock').html(h + ' ' + m);
        }

        up = !up;

        setTimeout(function () {
            startTime()
        }, 500);
    }
    startTime();
})();