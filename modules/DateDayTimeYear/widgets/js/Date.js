(function () {
    function checkTime(i) {
        return (i < 10) ? '0' + i : i;
    }

    function startTime() {
        let today = new Date(),
            d = checkTime(today.getDay()),
            m = checkTime(today.getMonth()),
            y = checkTime(today.getFullYear());

        $('#DateDayTimeYear_date').html(d + '.' + m + '.' + y);

        setTimeout(function () {
            startTime()
        }, 500);
    }
    startTime();
})();