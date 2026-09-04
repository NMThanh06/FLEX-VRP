/**
 * FLEX-VRP — Shared State
 * Biến trạng thái chia sẻ giữa các module.
 * Tất cả module khác import trạng thái từ đây.
 */

const AppState = {
    /** Danh sách điểm giao hàng hiện tại */
    deliveries: [],

    /** Hệ số thời tiết (1.0 = nắng, 1.3 = mưa nhẹ, 1.8 = mưa to) */
    weatherFactor: 1.0,

    /** Leaflet map instance */
    map: null,

    /** Marker của kho (depot) */
    depotMarker: null,

    /** Danh sách marker các điểm giao hàng */
    deliveryMarkers: [],

    /** Danh sách polyline đường đi trên bản đồ */
    routeLines: [],
};
