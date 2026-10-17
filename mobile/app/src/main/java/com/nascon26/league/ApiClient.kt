package com.nascon26.league

import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.*
import java.util.concurrent.TimeUnit

/**
 * REST API Client for communicating with the FastAPI backend on host port 8080.
 * Default for Android Emulator is http://10.0.2.2:8080/
 */
object ApiClient {
    var baseUrl: String = "http://10.0.2.2:8080/"
        set(value) {
            field = if (value.endsWith("/")) value else "$value/"
            retrofitInstance = null
        }

    private var retrofitInstance: Retrofit? = null

    private fun getRetrofit(): Retrofit {
        if (retrofitInstance == null) {
            val logging = HttpLoggingInterceptor().apply {
                level = HttpLoggingInterceptor.Level.BODY
            }
            val okHttpClient = OkHttpClient.Builder()
                .connectTimeout(5, TimeUnit.SECONDS)
                .readTimeout(10, TimeUnit.SECONDS)
                .addInterceptor(logging)
                .build()

            retrofitInstance = Retrofit.Builder()
                .baseUrl(baseUrl)
                .client(okHttpClient)
                .addConverterFactory(GsonConverterFactory.create())
                .build()
        }
        return retrofitInstance!!
    }

    val service: LeagueApiService by lazy {
        getRetrofit().create(LeagueApiService::class.java)
    }
}

interface LeagueApiService {
    @GET("health")
    suspend fun checkHealth(): Map<String, Any>

    @GET("api/v1/ping")
    suspend fun ping(): Map<String, Any>

    @GET("audit/v1/standings/{league_id}")
    suspend fun getStandings(@Path("league_id") leagueId: String): Map<String, Any>

    @GET("audit/v1/score/{match_id}")
    suspend fun getScore(@Path("match_id") matchId: String): Map<String, Any>

    @GET("audit/v1/inventory/{variant_id}")
    suspend fun getInventory(@Path("variant_id") variantId: String): Map<String, Any>

    @POST("audit/v1/checkout")
    suspend fun checkout(@Body body: Map<String, Any>): Map<String, Any>

    @POST("audit/v1/events")
    suspend fun appendEvent(@Body body: Map<String, Any>): Map<String, Any>

    @POST("audit/v1/roster/transfer")
    suspend fun transferPlayer(@Body body: Map<String, Any>): Map<String, Any>

    @POST("audit/v1/offline-sync")
    suspend fun syncOfflineActions(@Body body: Map<String, Any>): Map<String, Any>
}
