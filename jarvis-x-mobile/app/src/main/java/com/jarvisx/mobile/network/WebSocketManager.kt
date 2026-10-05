package com.jarvisx.mobile.network

import android.content.Context
import android.util.Log
import org.json.JSONObject

class WebSocketManager(
    private val context: Context,
    private val onCommandReceived: (action: String, requestId: String, phoneNumber: String, contactName: String) -> Unit = { _, _, _, _ -> }
) {
    private val TAG = "WebSocketManager"
    private var isConnected = false

    fun connect() {
        isConnected = true
        Log.d(TAG, "Phone Bridge WebSocket connected to JARVIS-X laptop server.")
    }

    fun disconnect() {
        isConnected = false
        Log.d(TAG, "Phone Bridge WebSocket disconnected.")
    }

    fun sendResponse(requestId: String, success: Boolean, event: String, message: String) {
        val payload = JSONObject().apply {
            put("request_id", requestId)
            put("success", success)
            put("event", event)
            put("message", message)
        }
        Log.d(TAG, "Sending phone bridge response: $payload")
    }

    fun handleIncomingMessage(jsonStr: String) {
        try {
            val obj = JSONObject(jsonStr)
            val action = obj.optString("action", "")
            val reqId = obj.optString("request_id", "")
            val params = obj.optJSONObject("parameters")
            val phone = params?.optString("phone_number", "") ?: ""
            val name = params?.optString("contact_name", "") ?: ""

            onCommandReceived(action, reqId, phone, name)
        } catch (e: Exception) {
            Log.e(TAG, "Parse error: ${e.message}")
        }
    }
}
