package com.jarvisx.mobile.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

@Composable
fun MainScreen() {
    var isConnected by remember { mutableStateOf(true) }
    var deviceName by remember { mutableStateOf("iQOO Neo 10R") }
    var batteryLevel by remember { mutableStateOf(88) }
    var lockStatus by remember { mutableStateOf("UNLOCKED") }

    val permissions = remember {
        listOf(
            "Phone Calls (CALL_PHONE)" to true,
            "Contacts (READ_CONTACTS)" to true,
            "Notifications (POST_NOTIFICATIONS)" to true,
            "Microphone (RECORD_AUDIO)" to true,
            "Camera (CAMERA)" to false,
            "Location (ACCESS_FINE_LOCATION)" to false
        )
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(Color(0xFF030D14))
            .padding(16.dp)
    ) {
        Text(
            text = "JARVIS-X MOBILE COMPANION",
            color = Color(0xFF00E5FF),
            fontSize = 18.sp,
            fontWeight = FontWeight.Bold
        )
        Text(
            text = "Device Control & Communication Bridge",
            color = Color.Gray,
            fontSize = 12.sp
        )

        Spacer(modifier = Modifier.height(16.dp))

        // Device Status Card
        Card(
            colors = CardDefaults.cardColors(containerColor = Color(0xFF091E2A)),
            modifier = Modifier.fillMaxWidth()
        ) {
            Column(modifier = Modifier.padding(16.dp)) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(text = "📱 $deviceName", color = Color.White, fontWeight = FontWeight.Bold)
                    Text(
                        text = if (isConnected) "● CONNECTED" else "○ OFFLINE",
                        color = if (isConnected) Color(0xFF00FF66) else Color.Red,
                        fontSize = 12.sp
                    )
                }

                Spacer(modifier = Modifier.height(8.dp))
                Text(text = "Battery: $batteryLevel% | Status: $lockStatus", color = Color.LightGray, fontSize = 12.sp)
                Text(text = "Auth State: AUTHENTICATED", color = Color(0xFF00E5FF), fontSize = 12.sp)
            }
        }

        Spacer(modifier = Modifier.height(16.dp))

        Text(
            text = "PERMISSIONS CENTER",
            color = Color(0xFF00E5FF),
            fontSize = 14.sp,
            fontWeight = FontWeight.Bold
        )

        Spacer(modifier = Modifier.height(8.dp))

        LazyColumn(
            verticalArrangement = Arrangement.spacedBy(8.dp),
            modifier = Modifier.fillMaxWidth()
        ) {
            items(permissions) { (permName, granted) ->
                Card(
                    colors = CardDefaults.cardColors(containerColor = Color(0xFF0D2535)),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(12.dp),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(text = permName, color = Color.White, fontSize = 13.sp)
                        Text(
                            text = if (granted) "✓ GRANTED" else "○ DENIED",
                            color = if (granted) Color(0xFF00FF66) else Color(0xFFFF4444),
                            fontSize = 12.sp,
                            fontWeight = FontWeight.Bold
                        )
                    }
                }
            }
        }
    }
}
