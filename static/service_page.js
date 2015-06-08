/**
 * Created by jangbi on 2015-06-04.
 */
$(document).ready(onLoad);

var map;

function onLoad() {
    // 지도 초기화
    map = L.map('map').setView([37.5, 127], 7);
	baseLayer = L.tileLayer('https://{s}.tiles.mapbox.com/v3/{id}/{z}/{x}/{y}.png', {
		maxZoom: 18,
		attribution: 'Map data &copy; <a href="http://openstreetmap.org">OpenStreetMap</a> contributors, ' +
			'<a href="http://creativecommons.org/licenses/by-sa/2.0/">CC-BY-SA</a>, ' +
			'Imagery © <a href="http://mapbox.com">Mapbox</a>',
		id: 'examples.map-20v6611k'
	}).addTo(map);

    // 좌표계 리스트 채우기
    $.getJSON("./capabilities", function(data) {
        var items = [];
        for (i in data.projections) {
            crs = data.projections[i];
            items.push('<option value="'+crs+'">'+crs.toUpperCase()+'</option>');
        }
        $("#crs").html(items.join(""))
    });

    // 버튼 동작 부착
    $("button").on("click", onClickButton);
    $("#address_input textarea").on("click", onClickTextarea);

    // progress
    progress = $( "#progressbar" ).progressbar({
      value: 0
    });


}

function onClickButton() {
    var id = $(this).attr("id");

    switch (id) {
        case "run":
            convertAddr();
            break;
        default :
            alert(id);
            break;
    }
}

// 입력 상자 클릭시 전체가 선택되게
function onClickTextarea() {
    $("#address_input textarea").select();
}


function stopConvert() {
    gStopFlag = true;
}

var markerGroup;
function convertAddr() {
    var data = $("#address_input textarea").val().trim().split("\n");
    var crs = $("#crs").val();

    // 변환결과 초기화
    $("#result_table table tbody").html("");
    if (markerGroup) map.removeLayer(markerGroup);
    markerGroup = L.layerGroup().addTo(map);

    // Modal dialog
    dialog = $("#dialog").dialog({
        autoOpen: false,
        height: 150,
        width: 350,
        modal: true,
        buttons: null
    });
    progress.progressbar("option", "value", 0);
    dialog.dialog( "open" );
    gStopFlag = false;

    gNumTotal = data.length;
    gNumProcessed = 0;
    progress.progressbar("option", "max", gNumTotal);

    for (var i in data) {
        var q = data[i];
        var url = "/geocoding/api?crs="+encodeURIComponent(crs)+"&q="+encodeURIComponent(q);

        if (gStopFlag) {
            gStopFlag = false;
            dialog.dialog( "close" );
            return;
        }

        $.getJSON(url, function(data) {
            progress.progressbar("option", "value", ++gNumProcessed);
            $("#percent").html((gNumProcessed*100/gNumTotal).toFixed(0));
            if (gNumProcessed >= gNumTotal) {
                gStopFlag = false;
                dialog.dialog( "close" );
            }

            if (!data.geojson) {
                $("#result_table table tbody").append("<tr><td>" + data.q + "</td><td colspan=7>변환 실패</td></tr>");

                return;
            }

            var x = data.x;
            var y = data.y;
            var lng = data.lng;
            var lat = data.lat;
            var address = data.address;
            var html = '<tr><td>'+data.q+'</td><td>'+address+'</td><td>'+ x.toFixed(2)+'</td><td>'+y.toFixed(2)+'</td>'
                +'<td>'+lng.toFixed(5)+'</td><td>'+lat.toFixed(5)+'</td><td>'+data.geojson.properties.service+'</td>'
                +'<td>'+data.sd+'</td><td>'+data.sim_ratio+'</td></tr>';
            $("#result_table table tbody").append(html);

            var marker = L.marker([lat, lng]);
            marker.bindPopup(address);
            marker.addTo(markerGroup);
        });
    }
}