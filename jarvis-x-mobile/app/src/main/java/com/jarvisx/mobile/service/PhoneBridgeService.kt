package com.jarvisx.mobile.service

import android.Manifest
import android.app.*
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.IBinder
import androidx.core.app.ActivityCompat
import androidx.core.app.NotificationCompat
import com.jarvisx.mobile.network.WebSocketManager

class PhoneBridgeService : Service() {
    private val CHANNEL_ID = "JARVIS_PHONE_BRIDGE_CHANNEL"
    private val NOTIF_ID = 1001
    private lateinit var webSocketManager: WebSocketManager

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
        val notification = NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("JARVIS-X Phone Bridge")
            .setContentText("Connected & Syncing Capabilities with Laptop")
            .setSmallIcon(android.R.drawable.stat_sys_data_bluetooth)
            .build()
        startForeground(NOTIF_ID, notification)

        webSocketManager = WebSocketManager(applicationContext) { action, requestId, phoneNumber, contactName ->
            handleCommand(action, requestId, phoneNumber, contactName)
        }
        webSocketManager.connect()
    }

    private fun handleCommand(action: String, requestId: String, phoneNumber: String, contactName: String) {
        if (action == "MAKE_CALL") {
            if (ActivityCompat.checkSelfPermission(this, Manifest.permission.CALL_PHONE) != PackageManager.PERMISSION_GRANTED) {
                webSocketManager.sendResponse(requestId, false, "PERMISSION_DENIED", "CALL_PHONE permission has not been granted.")
                return
            }
            try {
                val intent = Intent(Intent.ACTION_CALL).apply {
                    data = Uri.parse("tel:$phoneNumber")
                    flags = Intent.FLAG_ACTIVITY_NEW_TASK
                }
                startActivity(intent)
                webSocketManager.sendResponse(requestId, true, "CALL_DIALING", "Calling $contactName ($phoneNumber)")
            } catch (e: Exception) {
                webSocketManager.sendResponse(requestId, false, "CALL_FAILED", "Could not start call: ${e.message}")
            }
        }
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        return START_STICKY
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onDestroy() {
        webSocketManager.disconnect()
        super.onDestroy()
    }

    private fun createNotificationChannel() {
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "JARVIS-X Phone Bridge Service",
                NotificationManager.IMPORTANCE_LOW
            )
            val manager = getSystemService(NotificationManager::class.java)
            manager.createNotificationChannel(channel)
        }
    }
}
