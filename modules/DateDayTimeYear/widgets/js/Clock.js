(function () {
    let up = true;
    function checkTime(i) {
        return (i < 10) ? '0' + i : i;
    }

    function startTime() {
        let today = new Date(),
            h = checkTime(today.getHours()),
            m = checkTime(today.getMinutes());

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