(function () {
  "use strict";

  function sendToStreamlit(type, payload) {
    window.parent.postMessage(
      Object.assign({ isStreamlitMessage: true, type: type }, payload),
      "*"
    );
  }

  function setFrameHeight(height) {
    sendToStreamlit("streamlit:setFrameHeight", { height: height });
  }

  function setComponentValue(value) {
    sendToStreamlit("streamlit:setComponentValue", {
      value: value,
      dataType: "json",
    });
  }

  var gridApi = null;
  var anchorIndex = null;
  var selectedRows = new Set();
  var rowData = [];
  var suppressEmit = false;
  var lastRowsJson = "";
  var lastColumnsJson = "";
  var lastPinnedJson = "";
  var pinnedBottomRowData = [];
  var resizeObserver = null;
  var sortClickCounter = 0;
  var lastHeaderSortAt = 0;

  function fitColumnsToGrid(api) {
    if (!api || !api.sizeColumnsToFit) return;
    try {
      api.sizeColumnsToFit({ defaultMinWidth: 44 });
    } catch (err) {}
  }

  function observeGridResize(root) {
    if (resizeObserver) {
      resizeObserver.disconnect();
      resizeObserver = null;
    }
    if (!root || !window.ResizeObserver) return;
    resizeObserver = new ResizeObserver(function () {
      fitColumnsToGrid(gridApi);
    });
    resizeObserver.observe(root);
  }

  var FOOTER_BG = "#f0f2f6";
  var FOOTER_TEXT = "#31333F";

  function isFooterRow(data) {
    return !!(data && data.__isFooter);
  }

  function footerCellStyle(params) {
    if (isFooterRow(params.data)) {
      return { backgroundColor: FOOTER_BG, color: FOOTER_TEXT };
    }
    return null;
  }

  function gradientCellStyle(params) {
    if (isFooterRow(params.data)) {
      return { backgroundColor: FOOTER_BG, color: FOOTER_TEXT };
    }
    var styles = params.data && params.data.__styles;
    var field = params.colDef.field;
    if (styles && styles[field]) {
      return { backgroundColor: styles[field], color: "black" };
    }
    return { backgroundColor: "white", color: "black" };
  }

  function formatCellValue(value, format) {
    if (value == null || value === "" || (typeof value === "number" && isNaN(value))) {
      return "-";
    }
    if (format === "date" || format === "text") {
      return String(value);
    }
    var n = Number(value);
    if (isNaN(n)) {
      return String(value);
    }
    if (format === "currency") {
      return (
        "$" +
        n.toLocaleString("en-US", {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        })
      );
    }
    if (format === "currency0") {
      return (
        "$" +
        n.toLocaleString("en-US", {
          minimumFractionDigits: 0,
          maximumFractionDigits: 0,
        })
      );
    }
    if (format === "percent0") {
      return Math.round(n) + "%";
    }
    if (format === "percent2") {
      return n.toFixed(2) + "%";
    }
    if (format === "percent1") {
      return n.toFixed(1) + "%";
    }
    if (format === "shares") {
      return n.toLocaleString("en-US", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      });
    }
    if (format === "number2") {
      return n.toFixed(2);
    }
    if (format === "number0") {
      return n.toFixed(0);
    }
    if (format === "number1") {
      return n.toFixed(1);
    }
    return String(value);
  }

  function enrichColumnDefs(columnDefs) {
    return (columnDefs || []).map(function (col) {
      var next = Object.assign({}, col);
      if (next.gradient) {
        next.cellStyle = gradientCellStyle;
      } else {
        var prevStyle = next.cellStyle;
        next.cellStyle = function (params) {
          var footer = footerCellStyle(params);
          if (footer) return footer;
          if (typeof prevStyle === "function") return prevStyle(params);
          return prevStyle || null;
        };
      }
      if (next.cellFormat) {
        var fmt = next.cellFormat;
        delete next.cellFormat;
        next.valueFormatter = function (params) {
          return formatCellValue(params.value, fmt);
        };
      } else if (next.field !== "Symbol") {
        next.valueFormatter = function (params) {
          if (isFooterRow(params.data)) {
            var v = params.value;
            if (v == null || v === "" || (typeof v === "number" && isNaN(v))) {
              return "-";
            }
          }
          if (params.value == null || params.value === "") {
            return "-";
          }
          return params.value;
        };
        if (fmt !== "date" && fmt !== "text") {
          next.type = "numericColumn";
          next.comparator = function (valueA, valueB) {
            var a = valueA == null || valueA === "" ? null : Number(valueA);
            var b = valueB == null || valueB === "" ? null : Number(valueB);
            if (a == null && b == null) return 0;
            if (a == null) return 1;
            if (b == null) return -1;
            if (isNaN(a) && isNaN(b)) return 0;
            if (isNaN(a)) return 1;
            if (isNaN(b)) return -1;
            return a - b;
          };
        }
      }
      return next;
    });
  }

  function rowsToSymbols(indices) {
    return indices
      .map(function (idx) {
        var row = rowData[idx];
        return row && row.Symbol != null ? String(row.Symbol) : "";
      })
      .filter(function (sym) {
        return sym.length > 0;
      });
  }

  function isPinnedBottomNode(node) {
    return !!(node && (node.rowPinned === "bottom" || (node.data && node.data.__isFooter)));
  }

  function dataRowIndex(node) {
    if (!node || !node.data) return null;
    if (node.data.__isFooter) return null;
    if (node.rowPinned === "bottom") return null;
    if (node.data.__rowIndex != null) return parseInt(node.data.__rowIndex, 10);
    return node.rowIndex;
  }

  function pinnedRowsFromArgs(args) {
    var pinned = args && args.pinned_bottom_row;
    if (!pinned) return [];
    if (Array.isArray(pinned)) return pinned;
    return [pinned];
  }

  function updateSelectedRowsFromPython(selected) {
    selectedRows = new Set(
      (selected || [])
        .map(function (r) {
          return parseInt(r, 10);
        })
        .filter(function (r) {
          return !isNaN(r);
        })
    );
    if (selectedRows.size === 1) {
      anchorIndex = Array.from(selectedRows)[0];
    } else if (selectedRows.size === 0) {
      anchorIndex = null;
    }
  }

  function applySelection(api) {
    if (!api) return;
    api.deselectAll();
    api.forEachNode(function (node) {
      if (isPinnedBottomNode(node)) return;
      var idx = dataRowIndex(node);
      if (idx == null) return;
      if (selectedRows.has(idx)) {
        node.setSelected(true);
      }
    });
  }

  function emitComponentState(sortClick) {
    if (suppressEmit) return;
    var rows = Array.from(selectedRows).sort(function (a, b) {
      return a - b;
    });
    var payload = { rows: rows, symbols: rowsToSymbols(rows) };
    if (sortClick) {
      payload.sort_click = sortClick;
    }
    setComponentValue(payload);
  }

  function emitSelection() {
    emitComponentState(null);
  }

  function emitSortClick(columnField) {
    var now = Date.now();
    if (now - lastHeaderSortAt < 80) return;
    lastHeaderSortAt = now;
    sortClickCounter += 1;
    var rows = Array.from(selectedRows).sort(function (a, b) {
      return a - b;
    });
    setComponentValue({
      rows: rows,
      symbols: rowsToSymbols(rows),
      sort_click: {
        column: columnField,
        id: sortClickCounter,
      },
    });
  }

  function computeNextSelection(idx, event) {
    var shift = !!(event && event.shiftKey);
    var toggle = !!(
      event &&
      (event.ctrlKey || event.metaKey || event.altKey)
    );
    var next = new Set(selectedRows);

    if (shift && anchorIndex !== null) {
      next = new Set();
      var start = Math.min(anchorIndex, idx);
      var end = Math.max(anchorIndex, idx);
      for (var i = start; i <= end; i++) {
        next.add(i);
      }
      return next;
    }

    if (toggle) {
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    }

    anchorIndex = idx;
    return new Set([idx]);
  }

  function onRowClicked(params) {
    if (!params || !params.node) return;
    if (isPinnedBottomNode(params.node)) return;
    var idx = dataRowIndex(params.node);
    if (idx == null) return;
    selectedRows = computeNextSelection(idx, params.event);
    applySelection(params.api);
    emitSelection();
  }

  function destroyGrid() {
    if (resizeObserver) {
      resizeObserver.disconnect();
      resizeObserver = null;
    }
    if (gridApi && gridApi.destroy) {
      gridApi.destroy();
    }
    gridApi = null;
    lastRowsJson = "";
    lastColumnsJson = "";
    lastPinnedJson = "";
    pinnedBottomRowData = [];
  }

  function headerFieldFromClick(event) {
    if (!event || !event.target) return null;
    var cell = event.target.closest(".ag-header-cell");
    if (!cell) return null;
    var colId = cell.getAttribute("col-id");
    if (!colId || colId.indexOf("__") === 0) return null;
    return colId;
  }

  function onColumnHeaderClicked(params) {
    if (!params || !params.column) return;
    var field = params.column.getColDef().field;
    if (!field || field.indexOf("__") === 0) return;
    emitSortClick(field);
  }

  function bindHeaderClickFallback(root) {
    if (!root || root._peroHeaderSortBound) return;
    root._peroHeaderSortBound = true;
    root.addEventListener("click", function (event) {
      var field = headerFieldFromClick(event);
      if (!field) return;
      emitSortClick(field);
    });
  }

  function pinnedBottomRowStyle(params) {
    if (params.node && params.node.rowPinned === "bottom") {
      return { fontWeight: "600", backgroundColor: FOOTER_BG, color: FOOTER_TEXT };
    }
    return null;
  }

  function createGrid(root, columnDefs) {
    var options = {
      columnDefs: enrichColumnDefs(columnDefs),
      rowData: rowData,
      pinnedBottomRowData: pinnedBottomRowData.slice(),
      getRowStyle: pinnedBottomRowStyle,
      defaultColDef: {
        sortable: false,
        resizable: true,
        filter: false,
        flex: 1,
        minWidth: 44,
        wrapHeaderText: true,
        autoHeaderHeight: true,
        cellStyle: footerCellStyle,
        valueFormatter: function (params) {
          if (!isFooterRow(params.data)) return params.value;
          var v = params.value;
          if (v == null || v === "" || (typeof v === "number" && isNaN(v))) {
            return "-";
          }
          return params.value;
        },
      },
      autoSizeStrategy: {
        type: "fitGridWidth",
        defaultMinWidth: 44,
      },
      rowSelection: "multiple",
      suppressRowClickSelection: true,
      suppressCellFocus: true,
      animateRows: false,
      headerHeight: 32,
      rowHeight: 30,
      domLayout: "normal",
      getRowId: function (params) {
        if (params.data && params.data.__isFooter) return "__footer_sum__";
        return String(
          params.data.__rowIndex != null ? params.data.__rowIndex : params.node.rowIndex
        );
      },
      onRowClicked: onRowClicked,
      onColumnHeaderClicked: onColumnHeaderClicked,
      onGridReady: function (params) {
        fitColumnsToGrid(params.api);
        applySelection(params.api);
        bindHeaderClickFallback(root);
      },
      onFirstDataRendered: function (params) {
        fitColumnsToGrid(params.api);
      },
    };

    gridApi = agGrid.createGrid(root, options);
    observeGridResize(root);
  }

  function renderGrid(args) {
    var root = document.getElementById("grid-root");
    if (!root) return;

    rowData = Array.isArray(args.rows) ? args.rows : [];
    pinnedBottomRowData = pinnedRowsFromArgs(args);
    var height = parseInt(args.height, 10) || 320;
    setFrameHeight(height);

    var columnDefs = enrichColumnDefs(
      Array.isArray(args.column_defs) ? args.column_defs : []
    );
    updateSelectedRowsFromPython(args.selected_rows);

    var rowsJson = JSON.stringify(rowData);
    var columnsJson = JSON.stringify(columnDefs);
    var pinnedJson = JSON.stringify(pinnedBottomRowData);

    if (gridApi && columnsJson === lastColumnsJson) {
      if (rowsJson !== lastRowsJson) {
        gridApi.setGridOption("rowData", rowData);
        lastRowsJson = rowsJson;
      }
      if (pinnedJson !== lastPinnedJson) {
        gridApi.setGridOption("pinnedBottomRowData", pinnedBottomRowData.slice());
        lastPinnedJson = pinnedJson;
      }
      applySelection(gridApi);
      fitColumnsToGrid(gridApi);
      window.requestAnimationFrame(function () {
        fitColumnsToGrid(gridApi);
      });
      return;
    }

    if (gridApi && columnsJson !== lastColumnsJson) {
      gridApi.setGridOption("columnDefs", columnDefs);
      if (rowsJson !== lastRowsJson) {
        gridApi.setGridOption("rowData", rowData);
        lastRowsJson = rowsJson;
      }
      gridApi.setGridOption("pinnedBottomRowData", pinnedBottomRowData.slice());
      lastColumnsJson = columnsJson;
      lastPinnedJson = pinnedJson;
      applySelection(gridApi);
      fitColumnsToGrid(gridApi);
      bindHeaderClickFallback(root);
      return;
    }

    destroyGrid();
    root.innerHTML = "";
    lastRowsJson = rowsJson;
    lastColumnsJson = columnsJson;
    lastPinnedJson = pinnedJson;
    createGrid(root, columnDefs);
  }

  window.addEventListener("message", function (event) {
    var data = event.data;
    if (!data || data.type !== "streamlit:render") return;
    renderGrid(data.args || {});
  });

  sendToStreamlit("streamlit:componentReady", { apiVersion: 1 });
})();
