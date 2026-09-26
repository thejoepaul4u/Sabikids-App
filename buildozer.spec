[app]

title = Sabi Learners
package.name = sabilearners
package.domain = org.sabi

source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,json,txt,db,ttf,otf,mp3,mp4,wav
version = 0.1.0

requirements = python3,kivy==2.3.1,requests==2.32.3,charset-normalizer==3.4.3,pillow==10.4.0,plyer==2.1.0,pyjnius

android.api = 33
android.minapi = 24
android.ndk = 25b
android.archs = arm64-v8a
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE
android.enable_androidx = True
p4a.bootstrap = sdl2
p4a.ignore_setup_py = True
p4a.python_version = 3.11
android.accept_sdk_license = True
android.private_storage = True
android.entrypoint = org.kivy.android.PythonActivity
