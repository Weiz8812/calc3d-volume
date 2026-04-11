import streamlit as st

st.set_page_config(page_title='Calc3D Volume', layout='wide')
st.title('Calc3D Volume')
st.caption('Volume-only split scaffold from the original Calc3D Visualizer repository.')

st.info('This repository has been initialized as the dedicated volume app. The plotting, symbolic workflow, and numerical engine will be migrated in follow-up patches from the master repository.')

left, right = st.columns(2)
with left:
    st.subheader('Repository goal')
    st.write('- Keep only volume-related UI and outputs')
    st.write('- Support Cartesian and polar regions')
    st.write('- Restore symbolic and numerical volume workflows')

with right:
    st.subheader('Migration queue')
    st.write('1. Plotting interface')
    st.write('2. Volume controls')
    st.write('3. Numerical approximation')
    st.write('4. Symbolic steps and report export')

st.markdown('### Notes')
st.write('This first patch is only the repo scaffold so the split can proceed safely without touching the master app.')
