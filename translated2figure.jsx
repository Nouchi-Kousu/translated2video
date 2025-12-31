var doc = app.activeDocument;

if (!hasTranslationLayer(doc)) {
    alert("没有找到名为 '翻译' 或 'translation' 的图层组。");
    throw new Error("Missing translation layer group.");
}

// 保存无字背景
hideAllLayers(doc);
for (var i = 0; i < doc.layers.length; i++) {
    if (doc.layers[i].name != "翻译" && doc.layers[i].name != "translation")
        doc.layers[i].visible = true;
}
saveAsPNG(doc, "_000");

// 保存翻译文字图层
hideAllLayers(doc);
var translationLayer = getTranslationLayer(doc);
for (var i = translationLayer.layers.length - 1; i >= 0; i--) {
    translationLayer.layers[i].visible = true;
    saveAsPNG(doc, "_" + padStart(translationLayer.layers.length - i, 3, "0"));
    translationLayer.layers[i].visible = false;
}
alert("导出完成！", "信息");

// 检测是否存在翻译图层组
function hasTranslationLayer(d) {
    for (var j = 0; j < d.layers.length; j++)
        if (d.layers[j].name == "翻译" || d.layers[j].name == "translation")
            return true;
    return false;
}

// 隐藏所有图层；翻译图层组隐藏子图层
function hideAllLayers(d) {
    for (var j = 0; j < d.layers.length; j++)
        if (d.layers[j].name != "翻译" && d.layers[j].name != "translation")
            d.layers[j].visible = false;
        else
            for (var i = 0; i < d.layers[j].layers.length; i++)
                d.layers[j].layers[i].visible = false;
}

// 获取翻译图层组
function getTranslationLayer(d) {
    for (var j = 0; j < d.layers.length; j++)
        if (d.layers[j].name == "翻译" || d.layers[j].name == "translation")
            return d.layers[j];
    return null;
}

// 字符串左侧补齐
function padStart(str, length, padChar) {
    str = str + "";
    while (str.length < length) {
        str = padChar + str;
    }
    return str;
}

// 以 PNG 格式保存当前文档
function saveAsPNG(d, name) {
    var savePath = new File(
        d.path +
            "/" +
            d.name.split(".")[0] +
            "/" +
            d.name.split(".")[0] +
            name +
            ".png"
    );
    var exportOptions = new ExportOptionsSaveForWeb();
    exportOptions.format = SaveDocumentType.PNG;
    d.exportDocument(savePath, ExportType.SAVEFORWEB, exportOptions);
}
