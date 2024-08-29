import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import './Form.css';

function Form() {
    // State to store search type ('a', 'q', or empty string)
    const [searchType, setSearchType] = useState('');
    const [pubYear, setPubYear] = useState('');
    const [quarter, setQuarter] = useState('');
    const [message, setMessage] = useState('');
    const [error, setError] = useState(false);
    const [downloadLink, setDownloadLink] = useState('');
    const [loading, setLoading] = useState(false)
    const downloadLinkRef = useRef(null); // Ref to hold reference to <a> tag

    // Function to handle changes in search type input
    const handleSearchTypeChange = (e) => {
        setSearchType(e.target.value.toLowerCase());
        // Reset quarter when switching from quarterly to annual
        if (e.target.value.toLowerCase() === 'a') {
            setQuarter('');
        }
    };

    // Function to handle changes in publication year input
    const handlePubYearChange = (e) => {
        setPubYear(e.target.value);
    };

    // Function to handle changes in quarter input
    const handleQuarterChange = (e) => {
        setQuarter(e.target.value);
    };

    // Function to handle form submission
    const handleSubmitButton = async (e) => {
        e.preventDefault(); // Prevent default form submission behavior
        setLoading(true)

        // Ensure pubYear, searchType, and quarter are defined properly
        let formData = {
            publicationYear: pubYear,
            searchType: searchType,
            quarterNumber: quarter
        };

        try {
            const response = await axios.post('http://127.0.0.1:5000/scopus/data', formData);

            if (response.data.message === "Data received successfully") {
                setMessage("The file has been downloaded and is inside the system's download folder.");
                setError(false);
                // Set the download link state with the generated link
                setDownloadLink(`http://127.0.0.1:5000/scopus/download/${response.data.filename}`);
            } else {
                setMessage('There was some problem while creating/downloading the file.');
                setError(true);
            }
        } catch (error) {
            console.error('Error sending data to backend:', error);
            setMessage('There was an error communicating with the server.');
            setError(true);
        }
        finally{
            setLoading(false)
            setPubYear('');
            setSearchType('')
            setQuarter('');
        }
    };

    // Effect to trigger file download when downloadLink changes
    useEffect(() => {
        // if (downloadLink) {
        //     downloadLinkRef.current.click(); // Trigger click on the <a> tag
        // }
    }, [downloadLink]);

    return (
        <div className='formBody'>
            <form>
                <div id='initial'>
                    <label className='label'>Publication Year</label>
                    <input id='pub_year' type='text' placeholder='Enter year' value={pubYear} onChange={handlePubYearChange} />
                    <br />
                    <label className='label'>Is this search annual (A) or quarterly (Q)?</label>
                    <input id='search_type' type='text' placeholder='Enter A or Q' value={searchType} onChange={handleSearchTypeChange} />
                </div>
                <div id='details'>
                    {/* Conditional rendering based on searchType */}
                    {searchType === 'q' && (
                        <select name='quarter' value={quarter} onChange={handleQuarterChange}>
                            <option value=''>Select which quarter</option>
                            <option value='quarter_1'>Quarter 1</option>
                            <option value='quarter_2'>Quarter 2</option>
                            <option value='quarter_3'>Quarter 3</option>
                            <option value='quarter_4'>Quarter 4</option>
                        </select>
                    )}
                </div>
                <div className='submitBtn'>
                    <button type='submit' onClick={handleSubmitButton}>Submit</button>
                </div>
                <div id='result'>
                    {loading ? (<p className='label'>Form inputs submitted. File Creation is in progress.</p>):(<p className={error ? 'error' : 'success'} id='message'>{message}</p>)}
                    
                    {/* Hidden <a> tag to trigger file download */}
                    {/* <a ref={downloadLinkRef} href={downloadLink} style={{ display: 'none' }} download /> */}
                    {/* Display download button if downloadLink is available */}
                    {/* {downloadLink && (
                        <button onClick={() => downloadLinkRef.current.click()}>Download File</button>
                    )} */}
                </div>
            </form>
        </div>
    );
}

export default Form;
