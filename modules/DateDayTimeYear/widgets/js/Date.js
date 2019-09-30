(function () {
    function startTime() {
        let today = new Date();
        let d = String(today.getDay()).padStart(2, '0');
        let m = String(today.getMonth()).padStart(2, '0');
        let y = String(today.getFullYear());

        $('#DateDayTimeYear_date').html(d + '.' + m + '.' + y);

        setTimeout(function () {
            startTime()
        }, 500);
    }
    startTime();
})();