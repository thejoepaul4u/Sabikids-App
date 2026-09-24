[app]
title = Sabi Learners
package.name = sabilearners
package.domain = org.sabi

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,txt,db
version = 0.1

requirements = python3,kivy==2.2.1,kivymd==1.1.1,requests,pillow,pyjnius,plyer

orientation = portrait
fullscreen = 0

android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE
android.api = 33
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a,armeabi-v7a