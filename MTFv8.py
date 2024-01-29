# -*- coding: utf-8 -*-
"""
Spyder Editor

This is a temporary script file.
VERSION 3: 02/11/2023
MTF EXTRAIDA DEL PERFIL
INFO Y DEBUG IMPLEMENTADO
INTERPOLACION PARA CALCULAR LA MTF al 20%, 50% y 80%
AJUSTE CON SPLINES
RESUMEN GRAFICO
ARGUMENTOS OPTIMOS
VERSION 8: TKINTER
"""
import os, sys, argparse
import pydicom
import pylibjpeg
import numpy as np
import matplotlib.pyplot as plt
from skimage import measure, io, feature, exposure, filters, draw
from skimage.filters.rank import maximum
from scipy import ndimage as ndi
from scipy import interpolate
from scipy.fft import fft, fftfreq, ifft, rfft, fftshift, fft2
from scipy.optimize import curve_fit,root
from scipy.interpolate import interp1d
import matplotlib.pylab as pylab
from openpyxl import Workbook, load_workbook
from openpyxl.worksheet.table import Table, TableStyleInfo
import tkinter as tk
from tkinter import filedialog




def gauss(x,a,b):
    return a*np.exp(-1*b*x**2) 

def func(x,a,b,c,d,e):
        # g(x) = a2 * exp(-0.5 * (u - a1) / a3)^2 + a4 * exp(-abs(u - a1) / a5)
        return b*np.exp(-0.5*(x-a)/c)**2 + d*np.exp(-np.abs(x-a)/e)
    
def compute_mtf_num(x,y,thresolds, debug = False):
    dict_mtf = {}
    mtf = interp1d(x, y)
    for val in thresolds:
        print(' INFO **compute_mtf()** THRESOLDH MTF: ', val)
        for i in np.arange(0,max(x),0.1):
            if(debug): print(' DEBUG **compute_mtf()** Frecuencia(mm^-1) =  ', i, '   MTF: ', mtf(i))
            try:
                if (abs(mtf(i)-val) < 0.01): 
                    print(f" INFO **compute_mtf()** MTF at {val} is ", i)
                    dict_mtf[val] = i
            except:
                print(" WARNING **compute_mtf()** Something went wrong")
    return dict_mtf  

def compute_mtf(x,y,thresolds, debug = False):

    dict_mtf = {}
    for val in thresolds:
        print(' INFO **compute_mtf()** THRESOLDH MTF: ', val)
        xpos = x[len(x)//2:]
        ypos = y[len(y)//2:]
        y_i = min([i for i in ypos if i >= val])
        x_i = xpos[list(ypos).index(y_i)]
        y_iplus1 = max([i for i in ypos if i < val])
        x_iplus1 = xpos[list(ypos).index(y_iplus1)]
        m = (y_iplus1-y_i)/(x_iplus1-x_i)
        if y_i == val:
            mtf = x_i
        else:
            mtf = -(y_i-val)/m + x_i
        print(f" INFO **compute_mtf()** MTF at {val} is ", mtf)
        dict_mtf[val] = mtf
    return dict_mtf 

def fit_splines(x,xp,y):
       splines = interpolate.splrep(x, y)
       fxp = interpolate.splev(xp, splines)
       return fxp
   
def create_xlsx(mtf, mtf_thresholds, dcm_files):
    
    imagenes = dcm_files
    num_imagenes = len(imagenes)
    imagen = {}
    wb = Workbook()
    ws = wb.active
    ws.append(["Imagen", "Hospital", "Anatomía", "Equipo", "Tamaño de corte", "kV (V)", "I·t (mAs)", "Kernel", "Pitch", "CTDI", "TamPixelX (mm)", "TamPixelY (mm)", "NumPixelsRows", "NumPixelsCols", "Frecuencia MTF 10%","Frecuencia MTF 50%"])

    for k in range(num_imagenes):
        # 2. Leer cada imagen
        imagen[k] = pydicom.dcmread(imagenes[k], force = True)
        
        Hospital = imagen[k].InstitutionName
        ParteDelCuerpo = imagen[k].BodyPartExamined
        Equipo = imagen[k].ManufacturerModelName
        TamanoCorte = imagen[k].SliceThickness
        KV = imagen[k].KVP
        mAs = imagen[k].Exposure
        Kernel = imagen[k].ConvolutionKernel
        TamPixel = imagen[k].PixelSpacing
        tamPx = TamPixel[0]  # tamaño de Pixel en la exis.
        tamPy = TamPixel[1]  # tamaño de Pixel en la y.
        NumPixelsRows = imagen[k].Rows
        NumPixelsCols = imagen[k].Columns
        try:
            Pitch = imagen[k].SpiralPitchFactor
            CTDI = imagen[k].CTDIvol
        except:
            print('Bad Pitch value. Probably dataset not available. Adjust the value manually to continue!')
            Pitch = 99999
            CTDI = 99999
            pass
              
        #Hay que cambiar k por el nombre de la imagen
        row = [k, Hospital, ParteDelCuerpo, Equipo, TamanoCorte, KV, mAs, Kernel, Pitch, CTDI, tamPx, tamPy, NumPixelsRows, NumPixelsCols, mtf[k][mtf_thresholds[0]], mtf[k][mtf_thresholds[1]]]
        ws.append(row)
                        
    tab = Table(displayName="Table1", ref="A1:P40")
        
    # Add a default style with striped rows and banded columns
    style = TableStyleInfo(name="TableStyleMedium9", 
                               showFirstColumn=False,
                               showLastColumn=False, 
                               showRowStripes=True, 
                               showColumnStripes=True)
    tab.tableStyleInfo = style
    ws.add_table(tab)
    wb.save("table_mtf.xlsx")
    


def MTF(head_params, mtf_thresholds, info_file, dcm_files):
    # 1. Abrir las imágenes dcm.
    #print(' INFO **MTF()** LEYENDO IMAGEN: ', (os.path.dirname(os.getcwd()) + '/EjercicioMTF/imagenes/verificacion/Fm_hdn_rx_ct3Ccman.6.001.dcm'))
    #image_dir = os.path.dirname(os.getcwd()) + '/EjercicioMTF//imagenes/verificacion/Fm_hdn_rx_ct3Ccman.6.001.dcm'

    #print(dcm_files)
    #imagenes = [image_dir]
    imagenes = dcm_files
    num_imagenes = len(imagenes)
    
    mtfp_vals = {}
    info = pydicom.dcmread(info_file[0])
    
    for k in range(num_imagenes):
        # 2. Leer cada imagen
        #try:
        imagen = pydicom.dcmread(imagenes[k])
        pixel_data = imagen.pixel_array
        pixel_data_copy = imagen.pixel_array
        print(' INFO **MTF()** LEYENDO IMAGEN: ', imagenes[k])
        #except AttributeError:
        #    continue
        
        Hospital = info.InstitutionName
        ParteDelCuerpo = info.BodyPartExamined
        Equipo = info.ManufacturerModelName
        TamanoCorte = info.SliceThickness
        KV = info.KVP
        mAs = info.Exposure
        Kernel = info.ConvolutionKernel
        TamPixel = info.PixelSpacing
        tamPx = TamPixel[0]  # tamaño de Pixel en la exis.
        tamPy = TamPixel[1]  # tamaño de Pixel en la y.
        NumPixelsRows = info.Rows
        NumPixelsCols = info.Columns
        try:
            Pitch = info.SpiralPitchFactor
            CTDI = info.CTDIvol
        except:
            print('Bad Pitch Value. Probably dataset not available. Adjust the value manually to continue!')
            Pitch = 99999
            CTDI = 99999
            pass
            
    	# Get image dimensions
        height, width = pixel_data.shape[:2]	
    	# Compute the center coordinates
        roi_x = width/2 
        roi_y = height/2
        radius = int(150/tamPx) #en pixeles
        img = np.zeros(shape=pixel_data.shape)
        circle = plt.Circle((roi_y,roi_x), radius, color = 'red', fill = False)
        #ax.add_patch(circle)
        rr, cc = draw.disk((roi_x, roi_y), radius, shape=pixel_data.shape)
        img[rr, cc] = 1
        px = pixel_data[rr,cc]
        
        label_image = measure.label(img)
        props = measure.regionprops_table(label_image, pixel_data,
                      properties=['intensity_max','intensity_min'])


    
        # 3. Encontrar el maximo de la imagen
        image_max = ndi.maximum_filter(pixel_data,NumPixelsRows, mode = 'constant')

        image_pos = ndi.maximum_position(pixel_data,NumPixelsRows)

        #pixel_data_rescaled = filters.butterworth(pixel_data)
        plt.imshow(pixel_data, cmap = 'gray')
        # 4. Coordinadas del punto maximo
        # cuidado, estan invertidas las coordenadas( x->1, y->0)
        coordinates = feature.peak_local_max(pixel_data)
        #print(coordinates)
        Xm = coordinates[0][1]
        Ym = coordinates[0][0]
        #Xm = 261
        #Ym = 308
        
        # 5. Trazar un perfil entorno al máximo en la dirección exis
        A=20 
        lx=(Xm-A/2, Xm+A/2)
        ly=(Ym, Ym)
        start = (Ym, 0) #Start of the profile line
        end = (Xm, NumPixelsRows) #End of the profile line
        profile = measure.profile_line(pixel_data, (Ym, Xm - A/2), (Ym, Xm + A/2)) #Take the profile line
        
        # 5.1. GRAFICO DE LA IMAGEN DE PIXELES Y DEL PERFIL 
        fig, ax = plt.subplots(2, 1, figsize=(10, 10)) #Create the figures
        ax[0].imshow(pixel_data, cmap = 'gray') #Show the film at the top
        ax[0].plot(lx, ly, 'r-', lw=2) #Plot a red line across the film
        #ax[1].set_ylim(8000, 8600) #Plot a red line across the film        )
        ax[1].plot(profile)
        ax[1].grid()


        # 6. Perfil a mm
        xinf = (Xm-A/2) * tamPx
        xsup = (Xm+A/2) * tamPx
        profile_mm = profile
        fx = profile_mm
        fx = profile_mm / max(profile_mm)  # Normalizar el perfil.
        
        # 7. GRAFICO DEL PERFIL EN MM
        plt.figure(figsize=(12, 8))
        x = np.linspace(-(xsup-xinf)/2, (xsup-xinf)/2, len(fx))
        xp = np.linspace(-(xsup-xinf)/2, (xsup-xinf)/2, 5*len(fx)) #100??? it depends!!!
        fxp = fit_splines(x,xp,fx)
        plt.plot(x,fx, '*-', label='Perfil')
        plt.plot(xp,fxp, label = 'Ajuste')
        plt.xlabel('mm')
        plt.ylabel('f(x)')
        plt.title('PERFIL')
        plt.legend()
        

        # 8. CALCULO DE LA MTF PERFIL
        OTF = fft(fx)  # fft gives the zero frequency term at 0 component. While the others are positive and negative interval.
        OTFn = OTF[1:] #select all except the zero frequency term (because of non sense)

        MTF = np.abs(OTFn)  # valor absoluto.
        MTF = MTF/max(MTF)  # Normalizar y trasladar el cero al centro
        MTF = fftshift(MTF)  # Normalizar y trasladar el cero al centro
        
        # 8. CALCULO DE LA MTF AJUSTE
        OTFp = fft(fxp)  # fft gives the zero frequency term at 0 component. While the others are positive and negative interval.
        OTFnp = OTFp[1:] #select all except the zero frequency term (because of non sense)

        MTFp = np.abs(OTFnp)  # valor absoluto.
        MTFp = MTFp/max(MTFp)  # Normalizar y trasladar el cero al centro
        MTFp = fftshift(MTFp)  # Normalizar y trasladar el cero al centro

        
        # 8.1. Pasamos a espacio de frecuencias
        N = len(MTF)
        Np = len(MTFp)
        DX = np.abs(x[3]-x[2])  # distancia entre muestra (mm)
        DXp = np.abs(xp[3]-xp[2])  # distancia entre muestra (mm)
        F = 1/DX  # frecuencia espacial (1/mm)
        Fp = 1/DXp  # frecuencia espacial (1/mm)
        a = np.linspace(-N/2, N/2, N)  # puntos del dominio de frecuencia.
        ap = np.linspace(-Np/2, Np/2, Np)  # puntos del dominio de frecuencia.
        #a = np.arange(-N/2, N/2)  # puntos del dominio de frecuencia.
        #ap = np.arange(-Np/2, Np/2)  # puntos del dominio de frecuencia.

        Df = F / N  # intervalo de frecuencia (mm^-1)
        Dfp = Fp / Np  # intervalo de frecuencia (mm^-1)
        f = a*Df*10  # frecuencia ciclos/cm
        fp = ap*Dfp*10  # frecuencia ciclos/cm
        

        
        # 8.2. GRAFICO DE LA MTF
        plt.figure(figsize=(12, 8))
        plt.xlim(0,max(f)+1)
        plt.ylim(0,1.1)
        plt.plot(f, MTF, '*', label='MTF')
        plt.plot(fp, MTFp,'-*', label='MTFp')
        plt.grid(linewidth = 1)
        plt.yticks(np.arange(0,1.1,0.1))
        plt.xticks(np.arange(0,max(f),0.5))
        plt.xlabel('Frecuencia Espacial (ciclos/cm)')
        plt.ylabel('MTF')
        
        #VALUE OF MTF AT 10% and 50%
        #mtf_thresolds = [0.2,0.5]
        #mtf_thresolds = [0.5]
        try:
            mtf_vals = compute_mtf(f, MTF, mtf_thresholds)
            #print(' INFO **MTF()** Valores de la MTF Perfil al 10%, 50%: ', mtf_vals)
        except:
            mtf_vals = []
            #print(' INFO **MTF()** Valores de la MTF Perfil al 10%, 50%: ', mtf_vals)
            print('Something went wrong. Probably not enough points in range!')
            pass
        
        mtfp_vals[k] = {}
        mtfp_vals[k] = compute_mtf(fp, MTFp, mtf_thresholds)
        #print(' INFO **MTF()** Valores de la MTF Ajuste al 10%, 50%: ', mtfp_vals[k])
        
        # 9. RESUMEN GRÁFICO DEL ANALISIS DE LA MTF
        fig, axs = plt.subplots(2, 2)
        fig.set_figheight(15)
        fig.set_figwidth(15)
        params = {'axes.labelsize': 18,
          'axes.titlesize': 24,
          'xtick.labelsize':16,
          'ytick.labelsize':16,
          'legend.fontsize': 18}
        plt.rcParams.update(params)
        #plt.style.use('Solarize_Light2')
        #print(plt.style.available)
        
        #CONFIGURACION RESUMEN
        strings = [["Hospital: ", Hospital], ["Equipo: ", Equipo], ["Tamaño de corte: ", str(TamanoCorte)], ["kV: ", str(KV)], ["mAs: ", str(mAs)], ["Kernel: ", Kernel] ]
        config_string = '\n'.join(''.join(x) for x in strings)
        axs[0, 0].text(0.05, 0.90, config_string, fontsize = 19, va = 'top')
        axs[0, 0].set_title("CONFIGURACION", pad = 20)
        axs[0, 0].set_axis_off()
        #axs[0 ,0].set_facecolor("#1CC4AF")
        #PERFIL Y AJUSTE
        axs[1, 0].set_title("PERFIL Y AJUSTE")
        axs[1, 0].set_xlabel('mm')
        axs[1, 0].set_ylabel('f(x)')
        axs[1, 0].plot(x, fx, '*-', label='Perfil')
        axs[1, 0].plot(xp, fxp, '-', label='Ajuste')
        axs[1, 0].legend()
        #IMAGEN METF
        axs[0, 1].set_title("IMAGEN PARA CALCULAR LA MTF", pad = 20)
        axs[0, 1].imshow(imagen.pixel_array, cmap='gray')
        axs[0, 1].plot(Xm, Ym, 'ro', markersize=5)
        #PLOT MTF
        axs[1, 1].set_title("PLOT DE LA MTF")
        axs[1, 1].set_xlabel('Frecuencia Espacial (ciclos/cm)')
        axs[1, 1].set_ylabel('MTF')
        axs[1, 1].set_xlim(0,max(f))
        axs[1, 1].set_ylim(0, 1.1)
        axs[1, 1].grid(linewidth=2)
        axs[1, 1].plot(fp, MTFp,'-*', label='MTF', color = 'orange')
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.2)
        results = ['f (MTF = %i%%) = %.2f $\mathrm{cm}^{-1}$' %(10,mtfp_vals[k][mtf_thresholds[0]]), 'f (MTF = %i%%) = %.2f $\mathrm{cm}^{-1}$' %(50,mtfp_vals[k][mtf_thresholds[1]])]
        #results = ['f (MTF = %i%%) = %.2f $\mathrm{cm}^{-1}$' %(50,mtfp_vals[k][0.5])]
        textstr = '\n'.join(results)
        axs[1,1].text(0.30, 0.90, textstr, transform=axs[1,1].transAxes, fontsize=18,
        verticalalignment='top', bbox=props)
        plt.savefig('%s.png' %(imagenes[k]))
        plt.show()

    
    return mtfp_vals

def procesar_imagenes():
    path = ruta_texto.get()
    anatomia = seleccion_anatomia.get()
    head_params = anatomia == 'Head'
    
    os.chdir(path)
    dcm_files = []
    info_file = []
    for file_name in os.listdir(path):
        try:
            if file_name.endswith(".DCM"):
                dcm_files.append(os.path.join(path, file_name))
                print(' INFO **MAIN()** CARGANDO IMAGEN: ', file_name)
            elif file_name.endswith(".dcm"):
                if "info" in file_name:
                    info_file.append(os.path.join(path, file_name))
                    print(' INFO **MAIN()** CARGANDO ARCHIVO DE INFORMACION: ', file_name)
                else:
                    dcm_files.append(os.path.join(path, file_name))
                    print(' INFO **MAIN()** CARGANDO IMAGEN: ', file_name)
        except:
            pass

    mtf_thresholds = [0.1,0.5]
    #aqui necesito pillar el archivo sin comprimir para que encuentre bien el punto brillante
    #pero no contiene toda la info
    #asi que la info la pillo del archivo comprimido
    mtf = MTF(head_params, mtf_thresholds, info_file, dcm_files)
    ##create_xlsx(mtf, mtf_thresholds, dcm_files)
    
    # Por ahora, solo imprimiremos los valores seleccionados
    area_mensajes.insert(tk.END, f"Procesando imágenes en {path} para {anatomia}\n")

def seleccionar_carpeta():
    path = filedialog.askdirectory()
    ruta_texto.set(path)



app = tk.Tk()
app.title("Procesador de Imágenes DICOM")

# Ruta de los archivos DICOM
tk.Label(app, text="Ruta de los Archivos DICOM:").pack()
ruta_texto = tk.StringVar()
ruta_entrada = tk.Entry(app, textvariable=ruta_texto, width=50)
ruta_entrada.pack()
tk.Button(app, text="Seleccionar Carpeta", command=seleccionar_carpeta).pack()

# Selección de Anatomía
seleccion_anatomia = tk.StringVar(value='Head')
tk.Radiobutton(app, text="Head", variable=seleccion_anatomia, value='Head').pack()
tk.Radiobutton(app, text="Torax", variable=seleccion_anatomia, value='Torax').pack()

# Botón para procesar imágenes
tk.Button(app, text="Procesar Imágenes", command=procesar_imagenes).pack()

# Área de Mensajes
area_mensajes = tk.Text(app, height=10, width=50)
area_mensajes.pack()

app.mainloop()



  