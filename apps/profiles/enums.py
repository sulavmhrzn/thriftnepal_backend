from django.db import models


class Province(models.TextChoices):
    KOSHI = "koshi", "Koshi"
    MADHESH = "madhesh", "Madhesh"
    BAGMATI = "bagmati", "Bagmati"
    GANDAKI = "gandaki", "Gandaki"
    LUMBINI = "lumbini", "Lumbini"
    KARNALI = "karnali", "Karnali"
    SUDURPASHCHIM = "sudurpashchim", "Sudurpashchim"


class District(models.TextChoices):
    # Koshi Province
    BHOJPUR = "bhojpur", "Bhojpur"
    DHANKUTA = "dhankuta", "Dhankuta"
    ILAM = "ilam", "Ilam"
    JHAPA = "jhapa", "Jhapa"
    MORANG = "morang", "Morang"
    SUNSARI = "sunsari", "Sunsari"
    TAPLEJUNG = "taplejung", "Taplejung"

    # Madhesh Province
    BARA = "bara", "Bara"
    DHANUSA = "dhanusa", "Dhanusa"
    MAHOTTARI = "mahottari", "Mahottari"
    PARSA = "parsa", "Parsa"
    RAUTAHAT = "rautahat", "Rautahat"
    SAPTARI = "saptari", "Saptari"
    SIRAHA = "siraha", "Siraha"

    # Bagmati Province
    BHAKTAPUR = "bhaktapur", "Bhaktapur"
    CHITWAN = "chitwan", "Chitwan"
    DHADING = "dhading", "Dhading"
    KATHMANDU = "kathmandu", "Kathmandu"
    KAVREPALANCHOK = "kavrepalanchok", "Kavrepalanchok"
    LALITPUR = "lalitpur", "Lalitpur"
    MAKWANPUR = "makwanpur", "Makwanpur"
    NUWAKOT = "nuwakot", "Nuwakot"
    RAMECHHAP = "ramechhap", "Ramechhap"
    RASUWA = "rasuwa", "Rasuwa"
    SINDHULI = "sindhuli", "Sindhuli"

    # Gandaki Province
    BAGLUNG = "baglung", "Baglung"
    GORKHA = "gorkha", "Gorkha"
    KASKI = "kaski", "Kaski"
    LAMJUNG = "lamjung", "Lamjung"
    MANANG = "manang", "Manang"
    MYAGDI = "myagdi", "Myagdi"
    NAWALPUR = "nawalpur", "Nawalpur"
    PARBAT = "parbat", "Parbat"
    POKHARA = "pokhara", "Pokhara"
    SYANGJA = "syangja", "Syangja"
    TANAHUN = "tanahun", "Tanahun"

    # Lumbini Province
    ARGAKHANCHI = "argakhanchi", "Argakhanchi"
    BARDIYA = "bardiya", "Bardiya"
    CHITWAN_LUMBINI = "chitwan_lumbini", "Chitwan (Lumbini)"
    DANG = "dang", "Dang"
    GULMI = "gulmi", "Gulmi"
    KAPILVASTU = "kapilvastu", "Kapilvastu"
    NAWALPARASI = "nawalparasi", "Nawalparasi"
    PALPA = "palpa", "Palpa"
    RUPANDEHI = "rupandehi", "Rupandehi"

    # Karnali Province
    DAILEKH = "dailekh", "Dailekh"
    DOTI = "doti", "Doti"
    HUMLA = "humla", "Humla"
    JAJARKOT = "jajarkot", "Jajarkot"
    JUMLA = "jumla", "Jumla"
    KALIKOT = "kalikot", "Kalikot"
    MUGU = "mugu", "Mugu"
    SALYAN = "salyan", "Salyan"
    SURKHET = "surkhet", "Surkhet"
    ACHHAM = "achham", "Achham"

    # Sudurpashchim Province
    BAITADI = "baitadi", "Baitadi"
    BAJHANG = "bajhang", "Bajhang"
    BAJURA = "bajura", "Bajura"
    DADELDHURA = "dadeldhura", "Dadeldhura"
    DARCHULA = "darchula", "Darchula"
    KAILALI = "kailali", "Kailali"
    KANCHANPUR = "kanchanpur", "Kanchanpur"


class SocialPlatform(models.TextChoices):
    FACEBOOK = "facebook", "Facebook"
    INSTAGRAM = "instagram", "Instagram"
    TIKTOK = "tiktok", "TikTok"
    YOUTUBE = "youtube", "YouTube"
    TWITTER = "twitter", "Twitter"
