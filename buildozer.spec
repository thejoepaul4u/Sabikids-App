[app]

# Application identity
title = Sabi Learners
package.name = sabilearners
package.domain = org.sabi

# Project source
source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,json,txt,db,ttf,otf,mp3,wav
version = 0.1.0

# Python-for-Android requirements
requirements = python3,kivy==2.3.1,kivymd==2.0.0,requests==2.32.3,pillow==10.4.0,pyjnius,plyer

# Application display
orientation = portrait
fullscreen = 0

# Android configuration
android.api = 33
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a

# Required permissions
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE

# AndroidX
android.enable_androidx = True

# Build settings
p4a.bootstrap = sdl2
p4a.ignore_setup_py = True

# Accept the Android SDK license automatically
android.accept_sdk_license = True

# Keep the application data in the normal private application directory
android.private_storage = True

# Do not include unnecessary Java source files
android.add_src =

# Launch activity settings
android.entrypoint = org.kivy.android.PythonActivity